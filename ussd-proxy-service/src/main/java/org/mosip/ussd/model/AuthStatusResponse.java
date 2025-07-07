package org.mosip.ussd.model;

import java.util.List;

public class AuthStatusResponse {
    private String id;
    private String version;
    private String responsetime;
    private AuthResponse response;
    private List<ErrorDetail> errors;

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

    public String getResponsetime() {
        return responsetime;
    }

    public void setResponsetime(String responsetime) {
        this.responsetime = responsetime;
    }

    public AuthResponse getResponse() {
        return response;
    }

    public void setResponse(AuthResponse response) {
        this.response = response;
    }

    public List<ErrorDetail> getErrors() {
        return errors;
    }

    public void setErrors(List<ErrorDetail> errors) {
        this.errors = errors;
    }

    @Override
    public String toString() {
        return "AuthStatusResponse{" +
                "id='" + id + '\'' +
                ", version='" + version + '\'' +
                ", responsetime='" + responsetime + '\'' +
                ", response=" + response +
                ", errors=" + errors +
                '}';
    }
}



