package com.clinevo.inbox;

import com.clinevo.inbox.dto.EmailDetailDto;
import com.clinevo.inbox.dto.EmailSummaryDto;
import com.clinevo.inbox.entity.EmailStatus;
import com.clinevo.inbox.ingestion.EmailIngestionService;
import com.clinevo.inbox.service.EmailService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.List;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class EmailControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private EmailService emailService;

    @MockBean
    private EmailIngestionService ingestionService;

    @Test
    void shouldReturnEmailsList() throws Exception {
        EmailSummaryDto summary = EmailSummaryDto.builder()
                .id(1L)
                .messageId("<msg-1@clinic.org>")
                .senderEmail("doc@clinic.org")
                .subject("Adverse Reaction Report")
                .status(EmailStatus.RECEIVED)
                .receivedAt(Instant.now())
                .attachmentCount(1)
                .hasPdf(true)
                .build();

        when(emailService.getAllEmails()).thenReturn(List.of(summary));

        mockMvc.perform(get("/api/emails"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data[0].id").value(1))
                .andExpect(jsonPath("$.data[0].subject").value("Adverse Reaction Report"));
    }

    @Test
    void shouldTriggerMailboxPoll() throws Exception {
        when(ingestionService.pollAndIngest()).thenReturn(3);

        mockMvc.perform(post("/api/emails/poll"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.newlyIngestedCount").value(3));
    }
}
