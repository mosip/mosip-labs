package org.mosip.ussd.model;

public class AuthType {
    private String authType;
    private String authSubType;
    private boolean locked;
    private Integer unlockForSeconds;

    public String getAuthType() {
        return authType;
    }

    public void setAuthType(String authType) {
        this.authType = authType;
    }

    public String getAuthSubType() {
        return authSubType;
    }

    public void setAuthSubType(String authSubType) {
        this.authSubType = authSubType;
    }

    public boolean isLocked() {
        return locked;
    }

    public void setLocked(boolean locked) {
        this.locked = locked;
    }

    public Integer getUnlockForSeconds() {
        return unlockForSeconds;
    }

    public void setUnlockForSeconds(Integer unlockForSeconds) {
        this.unlockForSeconds = unlockForSeconds;
    }

    @Override
    public String toString() {
        return "AuthType{" +
                "authType='" + authType + '\'' +
                ", authSubType='" + authSubType + '\'' +
                ", locked=" + locked +
                ", unlockForSeconds=" + unlockForSeconds +
                '}';
    }
}