package org.mosip.ussd.IdServiceProvider;

public interface APICallback {
    public void onSuccess(Object param);
    public void onError(Object param);
}
