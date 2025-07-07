#FROM openjdk:8-jdk-alpine
FROM  arm64v8/openjdk
ARG JAR_FILE=*.jar
COPY ${JAR_FILE} app.jar
ENTRYPOINT ["java","-jar","/app.jar"]
EXPOSE 80

