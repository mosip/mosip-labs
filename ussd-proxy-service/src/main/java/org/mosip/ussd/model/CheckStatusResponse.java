package org.mosip.ussd.model;

import java.util.List;

public class CheckStatusResponse {
    private String id;
    private String version;
    private String responseTime;
    private CheckRIDStatus response;
    private List<CheckStatusError> errors;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getVersion() {
        return version;
    }

    public void setVersion(String version) {
        this.version = version;
    }

    public String getResponseTime() {
        return responseTime;
    }

    public void setResponseTime(String responseTime) {
        this.responseTime = responseTime;
    }

    public CheckRIDStatus getResponse() {
        return response;
    }

    public void setResponse(CheckRIDStatus response) {
        this.response = response;
    }

    public List<CheckStatusError> getErrors() {
        return errors;
    }

    public void setErrors(List<CheckStatusError> errors) {
        this.errors = errors;
    }

    @Override
    public String toString() {
        return "CheckStatusResponse{" +
                "id='" + id + '\'' +
                ", version='" + version + '\'' +
                ", responseTime='" + responseTime + '\'' +
                ", response=" + response +
                ", errors=" + errors +
                '}';
    }
}


