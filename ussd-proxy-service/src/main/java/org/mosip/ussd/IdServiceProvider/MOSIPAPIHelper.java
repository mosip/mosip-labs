package org.mosip.ussd.IdServiceProvider;

import org.apache.commons.lang3.RandomStringUtils;
import org.mosip.ussd.IdServiceProvider.models.APIResponse;
import org.mosip.ussd.IdServiceProvider.models.AuthHistory;
import org.mosip.ussd.IdServiceProvider.models.AuthRequest;

import org.mosip.ussd.IdServiceProvider.models.ChangeOfAddressRequest;
import org.mosip.ussd.IdServiceProvider.models.IdentityWrapper;

import org.mosip.ussd.IdServiceProvider.models.ResidentCredRequest;

import org.mosip.ussd.IdServiceProvider.models.ResidentHistoryRequest;
import org.mosip.ussd.IdServiceProvider.models.ResidentOTPRequest;
import org.mosip.ussd.IdServiceProvider.models.VIDRequest;


import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

import java.util.List;

import java.util.TimeZone;


import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class MOSIPAPIHelper {
    IDSAPI apiInterface;
    String authToken;
    List<AuthHistory> ret ;
    String retVal = "";

    String appId;
    String clientId;
    String clientSecret;
    String baseUrl;

    public String getAppId(){ return appId; }
    public String getClientId(){ return clientId; }
    public String getClientSecret(){ return clientSecret; }
    public String getBaseUrl(){ return baseUrl; }
    
    
    private static final Logger logger = LoggerFactory.getLogger(MOSIPAPIHelper.class);
   
    public static String getUTCDateTime(LocalDateTime time) {
        String DATEFORMAT = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'";
        DateTimeFormatter dateFormat = DateTimeFormatter.ofPattern(DATEFORMAT);
        if (time == null){
            time = LocalDateTime.now(TimeZone.getTimeZone("UTC").toZoneId());
        }
        String utcTime = time.format(dateFormat);
        return utcTime;
    }
    public static String genRandomNumbers(int targetStringLength) {
        String generatedString = RandomStringUtils.random(targetStringLength, false, true);

        return(generatedString);
    }
    public MOSIPAPIHelper(String baseUrl, String appId, String clientId, String clientSecret){
        this.baseUrl = baseUrl;
        this.appId = appId;
        this.clientId = clientId;
        this.clientSecret = clientSecret;

        new APISetup(baseUrl);
        apiInterface = APISetup.getClient().create(IDSAPI.class);

    }
    
   // public void authApp(String appId, String clientId, String clientSecret){

    public void authApp(){
        Object sync = new Object();

        Call<APIResponse> call = apiInterface.requestAuthWithSecret( createAuthReq(appId,clientSecret, clientId));
        call.enqueue(new Callback<APIResponse>() {
            @Override
            public void onResponse(Call<APIResponse> call, Response<APIResponse> response) {

                logger.debug("TAG",response.code()+"");
                logger.debug("TAG",response.body().getResponse().getMessage());

                if(response.code() == 200){
                    authToken = response.headers().get("Set-Cookie");
                    logger.debug("TAG", authToken);
     //               requestResidentOTP("5091326710","uin");
                }
                synchronized(sync){
                    sync.notify();
                }
            }
            @Override
            public void onFailure(Call<APIResponse> call, Throwable t) {
                call.cancel();
                synchronized(sync){
                    sync.notify();
                }
            }
        });
        synchronized(sync){
            try {
                sync.wait();
            } catch (InterruptedException e) {
                // TODO Auto-generated catch block
                e.printStackTrace();
            }
        }
    }

    public String requestVID(String id, String idType, String trId, String otp, String vidType, APICallback cb){

        Call<APIResponse> call = apiInterface.requestVID(createVIDReq(id,idType, trId,otp,vidType));
        call.enqueue(new Callback<APIResponse>() {
             @Override
             public void onResponse(Call<APIResponse> call, Response<APIResponse> response) {

                logger.info("TAG",response.code()+"");
                 if(response.code() == 200) {
                     if(response.body().getResponse() != null) {
                        logger.debug("TAG", response.body().getResponse().vid);
                         if(cb != null)
                             cb.onSuccess(response.body().getResponse().vid);
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
        return "";
    }
    /*
        Request OTP based on UIN/RID
     */
    public  Boolean requestResidentOTP(String id, String idType, String trId , APICallback cb){

        Call<APIResponse> call = apiInterface.requestResidentOTP(createResidentOTPReq(id,idType, trId));
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
    /*
    @RequiresApi(api = Build.VERSION_CODES.O)
    public  String requestResidentEUIN(String id, String idType, String otp, String trId){
        Call<APIResponse> call = apiInterface.requestResidentEUIN(createResidentEUINReq(id,idType,otp, trId));
        call.enqueue(new Callback<APIResponse>() {
            @RequiresApi(api = Build.VERSION_CODES.O)
            @Override
            public void onResponse(Call<APIResponse> call, Response<APIResponse> response) {
                Log.d("TAG",response.code()+"");
                if(response.code() == 200) {
                    if(response.body().getResponse() != null) {
                        Log.d("TAG", response.body().getResponse().getMessage());
                    }
                    else {
                        if(response.body().getErrors() != null){
                            Log.d("TAG", response.body().getErrors().toString());
                        }
                    }
                }
                else{
                    //      assert response.body() != null;
                    Log.d("TAG", response.message());
                }
            }
            @Override
            public void onFailure(Call<APIResponse> call, Throwable t) {
                call.cancel();
            }
        });
        return "";
    }
    */

    //private ExecutorService executor = Executors.newSingleThreadExecutor();

    public List<AuthHistory> requestResidentHistory(String id, String pageNumber, String otp, String trId, APICallback cb){
        Call<APIResponse> call = apiInterface.requestAuthHistory(createResidentHistoryReq(id,pageNumber,otp, trId));


         call.enqueue(new Callback<APIResponse>() {
            @Override
            public void onResponse(Call<APIResponse> call, Response<APIResponse> response) {

                logger.debug("TAG",response.code()+"");
                if(response.code() == 200) {
                    if(response.body().getResponse() != null) {
                        logger.debug("TAG", response.body().getResponse().getMessage());
                        logger.debug("count=", String.valueOf(response.body().getResponse().authHistory.size()));
                        ret =response.body().getResponse().authHistory;
                        if(cb != null){
                            cb.onSuccess(ret);
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
        return ret;
    }
    public void requestChangeOfAddress(String id, String idType, String otp, String trId, String[] addressLines, APICallback cb){


        Call<APIResponse> call = apiInterface.requestUpdateDemoData(createCOAReq(id,idType,otp, addressLines, trId));

        call.enqueue(new Callback<APIResponse>() {
            @Override
            public void onResponse(Call<APIResponse> call, Response<APIResponse> response) {

                logger.debug("TAG",response.code()+"");
                if(response.code() == 200) {
                    if(response.body().getResponse() != null) {
                        logger.debug("TAG", response.body().getResponse().getMessage());
                        logger.debug("regid=", response.body().getResponse().registrationId);
                        retVal = response.body().getResponse().registrationId;
                        if(cb != null){
                            cb.onSuccess(retVal);
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

    public static void openSaveAs(String nameAs){
        /* 
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("application/pdf"); //not needed, but maybe usefull
        intent.putExtra(Intent.EXTRA_TITLE, nameAs); //not needed, but maybe usefull
        App.getActivity().startActivityForResult(intent, 12001);
        */
    }
    /* 
    public static String saveToFile(byte[] barr, String fileName, Context ctx){
        ContentResolver resolver = ctx.getContentResolver();
        ContentValues contentValues = new ContentValues();
        contentValues.put(MediaStore.MediaColumns.DISPLAY_NAME, fileName );
        contentValues.put(MediaStore.MediaColumns.MIME_TYPE, "application/pdf");
        contentValues.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
        Uri pdfUri = resolver.insert(MediaStore.Files.getContentUri("external"), contentValues);


        try {
            OutputStream fos = resolver.openOutputStream(Objects.requireNonNull(pdfUri));
            fos.write(barr);
            fos.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return pdfUri.toString();
    }
    */
    public void downloadResidentCredentials(String reqid, APICallback cb){

        Call<ResponseBody> call = apiInterface.downloadResidentCredentials(reqid);

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
                        cb.onSuccess(retval);
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

        Call<APIResponse> call = apiInterface.getResidentCredRequestStatus(reqid);

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

    public void requestResidentCredentials(String id, String otp, String credType, String trId, APICallback cb){
        Call<APIResponse> call = apiInterface.requestResidentCredentials(createResidentCredReq(id,otp, credType,trId));

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

    private VIDRequest createVIDReq(String id, String idType, String trId, String otp, String vidType){
        VIDRequest req = new VIDRequest();
        req.data.individualId = id;
        req.data.individualIdType= idType;
        req.data.vidType= vidType;
        req.data.otp= otp;
        req.data.transactionID= trId;
        return req;
    }
    private ChangeOfAddressRequest createCOAReq(String id, String idType, String otp, String[] addressLines, String trId){
        ChangeOfAddressRequest req= new ChangeOfAddressRequest();
        IdentityWrapper identity = new IdentityWrapper(1);
        for(int i=0; i < 3; i++) {
            identity.identity.setAddress(i+1, 0, "eng", addressLines[i]);
        }
        identity.identity.UIN = id;
        req.data.setIdentityJson(identity);
        req.data.individualId = id;
        req.data.individualIdType = idType;
        req.data.transactionID = trId;
        req.data.otp = otp;

        return req;
    }

    private ResidentCredRequest createResidentCredReq(String id, String otp, String credType, String trId){
        ResidentCredRequest req = new ResidentCredRequest();
        req.data.otp = otp;
        req.data.individualId = id;
        req.data.credentialType= credType;
        req.data.transactionID = trId;
        req.data.encrypt =false;
       // req.data.additionalData.vid =id;
       // req.data.additionalData.registrationId =id;

        return req;
    }
    /*
    @RequiresApi(api = Build.VERSION_CODES.O)
    private ResidentEUINRequest createResidentEUINReq(String id, String idType, String otp, String trId) {
        ResidentEUINRequest req = new ResidentEUINRequest();
        req.data.individualId= id;
        req.data.individualIdType= idType;
        req.data.transactionID= trId;
        req.data.otp= otp;
        req.data.cardType="UIN";
        return req;
    }*/
    private ResidentHistoryRequest createResidentHistoryReq(String id, String pageNumber, String otp, String trId) {
        ResidentHistoryRequest req = new ResidentHistoryRequest();
        req.data.individualId= id;
        req.data.pageFetch= "500";
        req.data.transactionID= trId;
        req.data.otp= otp;
        req.data.pageStart = pageNumber;
        return req;
    }

    static ResidentOTPRequest createResidentOTPReq(String id, String idType, String trId) {
        ResidentOTPRequest req = new ResidentOTPRequest();

        req.individualId = id;
        req.individualIdType= idType;
        req.transactionID= trId;
        req.otpChannel= new String[]{"PHONE","EMAIL"};
        return req;
    }

    public static AuthRequest createAuthReq(String appId, String secretKey, String clientId){
        AuthRequest req = new AuthRequest();
        req.data.appId= appId; //  "resident"
        req.data.secretKey = secretKey;// "abc123";
        req.data.clientId=clientId; //"mosip-resident-client";
        return req;
    }

}
