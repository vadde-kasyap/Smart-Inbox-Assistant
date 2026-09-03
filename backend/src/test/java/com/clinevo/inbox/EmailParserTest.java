package com.clinevo.inbox;

import com.clinevo.inbox.dto.RawAttachment;
import com.clinevo.inbox.dto.RawEmail;
import com.clinevo.inbox.ingestion.EmailParser;
import com.clinevo.inbox.service.storage.StorageService;
import jakarta.mail.Session;
import jakarta.mail.internet.MimeBodyPart;
import jakarta.mail.internet.MimeMessage;
import jakarta.mail.internet.MimeMultipart;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Date;
import java.util.Properties;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class EmailParserTest {

    @Mock
    private StorageService storageService;

    private EmailParser emailParser;

    @BeforeEach
    void setUp() {
        emailParser = new EmailParser(storageService);
        when(storageService.computeSha256(any())).thenReturn("mock-sha256-hash-12345");
    }

    @Test
    void shouldParseMimeMessageWithPdfAttachment() throws Exception {
        Session session = Session.getDefaultInstance(new Properties());
        MimeMessage msg = new MimeMessage(session);
        msg.setFrom("dr.jones@hospital.org");
        msg.setSubject("Adverse Event Report: Drug X");
        msg.setSentDate(new Date());

        MimeMultipart multipart = new MimeMultipart();

        // Text body part
        MimeBodyPart textPart = new MimeBodyPart();
        textPart.setText("Patient had allergic reaction.", "UTF-8");
        multipart.addBodyPart(textPart);

        // PDF attachment part
        MimeBodyPart pdfPart = new MimeBodyPart();
        pdfPart.setDataHandler(new jakarta.activation.DataHandler(
                new jakarta.mail.util.ByteArrayDataSource(new byte[]{1, 2, 3, 4}, "application/pdf")));
        pdfPart.setFileName("case_report.pdf");
        pdfPart.setDisposition(MimeBodyPart.ATTACHMENT);
        multipart.addBodyPart(pdfPart);

        msg.setContent(multipart);
        msg.saveChanges();
        msg.setHeader("Message-ID", "<test-msg-001@pharma.org>");

        RawEmail rawEmail = emailParser.parse(msg);

        assertThat(rawEmail).isNotNull();
        assertThat(rawEmail.getMessageId()).isEqualTo("<test-msg-001@pharma.org>");
        assertThat(rawEmail.getSender()).contains("dr.jones@hospital.org");
        assertThat(rawEmail.getSubject()).isEqualTo("Adverse Event Report: Drug X");
        assertThat(rawEmail.getBody()).contains("Patient had allergic reaction.");
        assertThat(rawEmail.getAttachments()).hasSize(1);

        RawAttachment att = rawEmail.getAttachments().get(0);
        assertThat(att.getFilename()).isEqualTo("case_report.pdf");
        assertThat(att.isPdf()).isTrue();
        assertThat(att.getSha256()).isEqualTo("mock-sha256-hash-12345");
    }
}
