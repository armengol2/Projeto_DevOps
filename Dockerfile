FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /build

# Copia só o pom primeiro: o Docker reaproveita o cache das dependências
# enquanto o pom.xml não mudar
COPY pom.xml .
RUN mvn -B -q dependency:go-offline

COPY src ./src
# Os testes rodam no pipeline do Jenkins, não no build da imagem
RUN mvn -B -q clean package -DskipTests

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

RUN addgroup -S app && adduser -S app -G app
COPY --from=build /build/target/*.jar app.jar
USER app

ENV DB_URL=jdbc:postgresql://postgres:5432/chamados \
    DB_USER=chamados

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
