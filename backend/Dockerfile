# Stage 1: Build JAR using Maven with Temurin JDK 21
FROM maven:3.9.8-eclipse-temurin-21 AS builder
WORKDIR /build

# Copy pom.xml and download dependencies for faster cached rebuilds
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copy source and package
COPY src ./src
RUN mvn clean package -DskipTests -B

# Stage 2: Minimal JRE Runtime
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

# Install curl for docker healthcheck
RUN apk add --no-cache curl

# Create storage directory
RUN mkdir -p /app/storage /app/test-data/emails

# Copy compiled jar
COPY --from=builder /build/target/smart-inbox-backend-1.0.0-SNAPSHOT.jar /app/app.jar

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
  CMD curl -f http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["java", "-Djava.security.egd=file:/dev/./urandom", "-jar", "/app/app.jar"]
