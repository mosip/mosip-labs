package org.mosip.ussd.model;

public class CheckRIDStatus {
    private String ridStatus;

    public String getRidStatus() {
        return ridStatus;
    }

    public void setRidStatus(String ridStatus) {
        this.ridStatus = ridStatus;
    }

    @Override
    public String toString() {
        return "CheckRIDStatus{" +
                "ridStatus='" + ridStatus + '\'' +
                '}';
    }
}