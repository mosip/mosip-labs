package org.mosip.ussd.IdServiceProvider;
import org.mosip.ussd.IdServiceProvider.models.APIResponse;
import org.mosip.ussd.IdServiceProvider.models.DownloadRequest;
import org.mosip.ussd.IdServiceProvider.models.ResidentCredRequest2;
import org.mosip.ussd.IdServiceProvider.models.ResidentOTPRequest2;
import java.io.IOException;
import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class IDCredsHelper {
    IDCredsAPI apiInterface;
    
    String baseUrl;
    String retVal = "";
    public void setBaseUrl(String url){
        baseUrl = url;
    }
    public String getBaseUrl(){ return baseUrl; }
    
    
    private static final Logger logger = LoggerFactory.getLogger(MOSIPAPIHelper.class);
   
    public IDCredsHelper(String baseUrl){
        this.baseUrl = baseUrl;
      
        apiInterface = APISetup.getClient(baseUrl).create(IDCredsAPI.class);

    }
    
    /*
        Request OTP based on UIN/RID
     */
    public  Boolean requestResidentOTP(String id, String idType, String trId , APICallback cb){

        Call<APIResponse> call = apiInterface.requestOTP(createOTPReq2(id,idType, trId));
        call.enqueue(new Callback<APIResponse>() {
            @Override
            public void onResponse(Call<APIResponse> call, Response<APIResponse> response) {

                logger.debug("TAG",response.code()+"");
                if(response.code() == 200) {
                    if(response.body().getResponse() != null) {
                        logger.debug("TAG", response.body().getResponse().maskedMobile);
                        if(cb != null)
                            cb.onSuccess("OTP request sent successfully");
                    }
                    else {
                        if(response.body().getErrors() != null){
                            logger.debug("TAG", response.body().getErrors().toString());
                            if(cb != null)
                                cb.onError (response.body().getErrors().toString());

                        }
                    }

                }
                else{
              //      assert response.body() != null;
                    logger.debug("TAG", response.message());
                    if(cb != null)
                        cb.onError (response.message());

                }

            }
            @Override
            public void onFailure(Call<APIResponse> call, Throwable t) {
                call.cancel();
            }
        });
        return true;
    }
   
   
    public void downloadResidentCredentials(String reqId,String individualId, APICallback cb){
        DownloadRequest req = new DownloadRequest();
        req.setIndividualId(individualId);
        req.setRequestId(reqId);
        Call<ResponseBody> call = apiInterface.downloadCredentials(req);

        call.enqueue(new Callback<ResponseBody>() {
            @Override
            public void onResponse(Call<ResponseBody> call, Response<ResponseBody> response) {
                byte[] retval = null;
                logger.debug("TAG", response.code() + "");
                if (response.code() == 200) {
                    try {
                        retval = response.body().bytes();
                    } catch (IOException e) {
                        e.printStackTrace();
                    }

                    if (cb != null) {
                        cb.onSuccess(new String(retval));
                    }
                } else {
                    //      assert response.body() != null;
                    logger.debug("TAG", response.message());

                }
            }

            @Override
            public void onFailure(Call<ResponseBody> call, Throwable t) {
                call.cancel();
            }
        });

    }
    public void getResidentCredentialRequestStatus(String reqid, APICallback cb){

        Call<APIResponse> call = apiInterface.getCredRequestStatus(reqid);

        call.enqueue(new Callback<APIResponse>() {
            @Override
            public void onResponse(Call<APIResponse> call, Response<APIResponse> response) {
                String retval = "";
                logger.debug("TAG",response.code()+"");
                if(response.code() == 200) {
                    if(response.body().getResponse() != null) {
                        retval = response.body().getResponse().statusCode;
                        logger.debug("TAG", retval);

                        if(cb != null){
                            cb.onSuccess(retval);
                        }
                    }
                    else {
                        if(response.body().getErrors() != null){
                            logger.debug("TAG", response.body().getErrors().toString());
                            if(cb != null){
                                cb.onError(response.body().getErrors());
                            }

                        }
                    }

                }
                else{
                    //      assert response.body() != null;
                    logger.debug("TAG", response.message());

                }

            }
            @Override
            public void onFailure(Call<APIResponse> call, Throwable t) {
                call.cancel();
            }
        });

    }

    public void requestResidentCredentials(String id, String otp, String idType, String trId, APICallback cb){
        Call<APIResponse> call = apiInterface.requestCredentials(createResidentCredReq(id,otp, idType,trId));

        call.enqueue(new Callback<APIResponse>() {
            @Override
            public void onResponse(Call<APIResponse> call, Response<APIResponse> response) {

                logger.debug("TAG",response.code()+"");
                if(response.code() == 200) {
                    if(response.body().getResponse() != null) {
                       // Log.d("TAG", response.body().getResponse().getMessage());
                       logger.debug("Request ID=", response.body().getResponse().requestId);

                        if(cb != null){
                            cb.onSuccess(response.body().getResponse().requestId);
                        }
                    }
                    else {
                        if(response.body().getErrors() != null){
                            logger.debug("TAG", response.body().getErrors().toString());
                            if(cb != null){
                                cb.onError(response.body().getErrors());
                            }

                        }
                    }

                }
                else{
                    //      assert response.body() != null;
                    logger.debug("TAG", response.message());

                }

            }
            @Override
            public void onFailure(Call<APIResponse> call, Throwable t) {
                call.cancel();
            }
        });

    }

   
    private ResidentCredRequest2 createResidentCredReq(String id, String otp, String idType, String trId){
        ResidentCredRequest2 req = new ResidentCredRequest2();
        req.otp = otp;
        req.individualId = id;
        req.individualIdType= idType;
        req.transactionID = trId;
     
    
        return req;
    }
   
   
    static ResidentOTPRequest2 createOTPReq2(String id, String idType, String trId) {
        ResidentOTPRequest2 req = new ResidentOTPRequest2();

        req.individualId = id;
        req.individualIdType= idType;
        req.transactionID= trId;
        req.otpChannel= new String[]{"PHONE","EMAIL"};
        return req;
    }

   
}
