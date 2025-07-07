package org.mosip.ussd.model;

import java.util.List;

public class AuthResponse {
    private List<AuthType> authTypes;

    public List<AuthType> getAuthTypes() {
        return authTypes;
    }

    public void setAuthTypes(List<AuthType> authTypes) {
        this.authTypes = authTypes;
    }

    @Override
    public String toString() {
        return "AuthResponse{" +
                "authTypes=" + authTypes +
                '}';
    }
}