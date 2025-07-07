package org.mosip.ussd.util;


import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.List;

import org.apache.http.client.ClientProtocolException;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpPost;

import org.apache.http.entity.StringEntity;

import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;

import org.mosip.ussd.IdServiceProvider.APICallback;
import org.mosip.ussd.IdServiceProvider.IDCredsHelper;
import org.mosip.ussd.IdServiceProvider.MOSIPAPIHelper;
import org.mosip.ussd.entity.Credentials;
import org.mosip.ussd.service.CredentialService;


import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.StepContribution;
import org.springframework.batch.core.scope.context.ChunkContext;
import org.springframework.batch.core.step.tasklet.Tasklet;
import org.springframework.batch.repeat.RepeatStatus;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class CredentialTask implements Tasklet{
    Object syncObject;
    MOSIPAPIHelper idProvider;
    IDCredsHelper idCredsProvider;
    Boolean useCredsAPI ;
    String requestId;
    String err;
    Boolean bOnlyDownload;
    String residentId;

    CredentialService credService;
    
    private static final Logger logger = LoggerFactory.getLogger(CredentialTask.class);
  
    public CredentialTask(CredentialService cService){
        credService = cService;
    }
  
    Credentials saveCreds2Wallet(String creds){
        Credentials cred = new Credentials();
        cred.setContent(creds);
        cred.setName("VC");
        cred.setResidentId(residentId);

        return credService.addCredential(cred);
    }
    String loadCredsFromWallet(String credId){
        String credStr = null;
        Long id = Long.parseLong(credId);
        List<Credentials> creds = credService.getAllCredentials(residentId);
        if(creds != null && !creds.isEmpty() ){
            for(Credentials cr: creds){
                if(cr.getId() == id){
                    credStr = cr.getContent();
                    break;
                }
            }
        }
        return credStr;
    }
    //debug - save creds to file
    String save2File(String creds) {
        try{
            try(FileOutputStream fileOutputStream = new FileOutputStream("credential.json")){
                fileOutputStream.write(creds.getBytes());
            }
        }catch(Exception e){
            e.printStackTrace();
        }
       return "credential.json";
        
    }
    void PushToRP(String partnerId, String partnerUrl, String partnerKey,String applicationId, String creds) throws  ClientProtocolException, IOException, ParseException{
     //   Optional<Partner> ret = partnerRepository.findById(partnerId);
     //   if(ret.isPresent()){
     //       String url = ret.get().getPartnerUrl();
            logger.info("partner url:"+ partnerUrl);
            //String filePath =save2File(creds);
            CloseableHttpClient httpclient = HttpClients.createDefault();
            HttpPost httppost = new HttpPost(partnerUrl);
            JSONParser parser = new JSONParser();
		    JSONObject credsJson = (JSONObject) parser.parse(new String(creds));
			//JSONObject credObject= (JSONObject) credsJson.get("credential");
		    JSONObject vcObject = (JSONObject) credsJson.get("verifiableCredential");
            ((JSONObject)vcObject.get("credentialSubject")).remove("biometrics");
            JSONObject jsonObject = new JSONObject();
            save2File(vcObject.toJSONString());
            
            jsonObject.put("partnerId", partnerId);
            jsonObject.put("applicationId", applicationId);
            jsonObject.put("name", "VC");
            jsonObject.put("value", vcObject.toJSONString());

            StringEntity body = new StringEntity(jsonObject.toString());
            httppost.setHeader("Content-type", "application/json");
           // MultipartEntityBuilder entitybuilder = MultipartEntityBuilder.create();
           // entitybuilder.setMode(HttpMultipartMode.BROWSER_COMPATIBLE);
           // entitybuilder.addBinaryBody("credentials", new File(filePath));
           // HttpEntity mutiPartHttpEntity = entitybuilder.build(); 
           // RequestBuilder reqbuilder = RequestBuilder.post(partnerUrl);
           // reqbuilder.setEntity(mutiPartHttpEntity);
            //HttpUriRequest multipartRequest = reqbuilder.build();
            //HttpResponse httpresponse = httpclient.execute(multipartRequest);
            httppost.setEntity(body);

            CloseableHttpResponse httpresponse = httpclient.execute(httppost);
            org.apache.http.HttpEntity entity = httpresponse.getEntity();
            logger.info(httpresponse.getStatusLine().toString());
            if (entity != null) {
                try (InputStream instream = entity.getContent()) {
                    // do something useful
                    byte[] data= instream.readAllBytes();
                    String retval = new String(data);
                    logger.info(retval);
                }
            }
        //}
        //else{
        //    logger.error("invalid partnerId "+ partnerId);
       // }

    }

    @Override
    public RepeatStatus execute(StepContribution contrib, ChunkContext context) throws Exception {
      
        JobParameters params = context.getStepContext().getStepExecution().getJobParameters();

        logger.info( "execute:" +
        context.getStepContext().getStepExecution().getJobParameters().getString("idprovider"));
      //  idProvider = (MOSIPAPIHelper) params.getParameters().get("idProvider").getValue();
        String sessionId = params.getString("sessionId");
        //UssdSession state = (UssdSession) params.getParameters().get("ussdSession").getValue();
       
       String uin =  params.getString("uin");
       String otp =  params.getString("otp");
       String trId  = params.getString("TrId");

       String partnerId =  params.getString("partnerId");
       String applicationId =  params.getString("applicationId");
       String partnerUrl = params.getString("partnerUrl");
       String partnerKey = params.getString("partnerKey");
       String credentialId = params.getString("credentialId");
        residentId = params.getString("residentId");
       Long intUseCredsAPI = params.getLong("useCredsAPI");
       useCredsAPI = intUseCredsAPI == 1L ? true: false;

       Long intdownload = params.getLong("onlyDownload");
       bOnlyDownload = intdownload ==1L ? true: false;

       if(!bOnlyDownload){
        String creds = loadCredsFromWallet(credentialId);
        if(creds != null)
            PushToRP( partnerId, partnerUrl, partnerKey, applicationId, creds);
        return RepeatStatus.FINISHED;
       }

       if(useCredsAPI){
        idCredsProvider = new IDCredsHelper(params.getString("baseUrl"));
       }
       else{
            idProvider = new  MOSIPAPIHelper(
                            params.getString("baseUrl"),
                            params.getString("appId"),
                            params.getString("clientId"),
                            params.getString("clientSecret")
                     );
            idProvider.authApp();
       }
       APICallback callback = new APICallback(){

        @Override
        public void onSuccess(Object param) {
            //Push to RP Service
            
                if(bOnlyDownload){
                    //Save param to Resident table
                    saveCreds2Wallet(param.toString());
                }
                else {
               //     String creds = loadCredsFromWallet();
               //     PushToRP( partnerId, partnerUrl, partnerKey, applicationId, creds);
                }
            
        }

        @Override
        public void onError(Object param) {
            
        }

       };

        String resp = processCredTransfer( sessionId,  uin, otp,trId, partnerId, applicationId, callback);
    
        logger.info("CredentialTask done" + resp);
       
        return RepeatStatus.FINISHED;
    }
    
    String downloadCredentialsRequest(String uin, String otp, String TrId) throws InterruptedException{

        syncObject = new Object();
      
    
        APICallback cb =  new APICallback() {
    
            @Override
            public void onSuccess(Object param) {
                requestId = param.toString();
                logger.info("requestResidentCredentials: requestId="+ requestId);
                synchronized(syncObject){
                    syncObject.notifyAll(); 
                }
            }
    
            @Override
            public void onError(Object param) {
                err = param.toString();
                synchronized(syncObject){
                    syncObject.notifyAll(); 
                }
                
            }
            
        };
        
        
        if(useCredsAPI)
            idCredsProvider.requestResidentCredentials(uin, otp, Util.ID_TYPE, TrId, cb);
        else
            idProvider.requestResidentCredentials(uin, otp, "euin", TrId,cb);

        synchronized(syncObject){
            syncObject.wait();
        }
        return requestId;
    }
       
    private Boolean processDownload(String requestId, String uin , APICallback callback) throws InterruptedException{
        Object syncObject = new Object();

        logger.info("downloadResidentCredentials :before");

        APICallback cb =  new APICallback() {

            @Override
            public void onSuccess(Object param) {
                    // Push the downloaded PDF to partner URL
                    //TODO: Add push code
                isDone = true;
                logger.info("downloaded creds:");//+ param.toString());
                //PUSH to RP Service
               
                if(callback != null)
                callback.onSuccess(param.toString());

                synchronized(syncObject){
                    syncObject.notify();
                }
                    
            }

            @Override
            public void onError(Object param) {
                err = param.toString();
                isDone = true;
                if(callback != null)
                callback.onError(err);
                synchronized(syncObject){
                    syncObject.notify();
                }
                    
            }
                
        };

        //need to add a delay 10 sec
        Thread.sleep(10000);
        if(useCredsAPI){
            logger.info("downloaded creds:idCredsProvider:" + requestId + ","+ uin);//+ param.toString());
         
            idCredsProvider.downloadResidentCredentials(requestId,uin,cb);
        }
        else
            idProvider.downloadResidentCredentials(requestId,cb);
        synchronized(syncObject){
            syncObject.wait();
        }
        return isDone;
    }
    Boolean isDone ;     
    String processCredTransfer(String sessionId, String uin, String otp,String trId, String partnerId, String applicationId, APICallback callback){
        
        Object syncObject = new Object();
        isDone = false;    
        try {
            String requestId = downloadCredentialsRequest(uin,  otp,trId);
            if(requestId != null){

                APICallback cb =  new APICallback() {

                    @Override
                    public void onSuccess(Object param) {
                        logger.info("requestResidentCredentials: status="+ param.toString());
                        //printing
                        if( param.toString().equals(Util.CRED_STATUS_PRINTING) ||
                            param.toString().equals(Util.CRED_STATUS_ISSUED) ){
                                //download credentials
                            logger.info("downloadResidentCredentials :before");
                            try {
                                processDownload(requestId,uin,callback);
                            } catch (InterruptedException e) {
                                // TODO Auto-generated catch block
                                e.printStackTrace();
                            }
       
                        }
                        else{
                            synchronized(syncObject){
                                syncObject.notify();
                            }
                        }
                        
                         
                            
                    }

                    @Override
                    public void onError(Object param) {
                        err = param.toString();
                        isDone = true;
                        synchronized(syncObject){
                            syncObject.notify();
                        }
                            
                    }
                        
                };
                while(!isDone){
                    logger.info("getResidentCredentialRequestStatus: requestId="+ requestId);
                    Thread.sleep(5000);
                    if(useCredsAPI)
                        idCredsProvider.getResidentCredentialRequestStatus(requestId, cb);
                    else
                        idProvider.getResidentCredentialRequestStatus(requestId, cb);

                    synchronized(syncObject){
                        try {
                            syncObject.wait();
                        } catch (InterruptedException e) {
                               
                            e.printStackTrace();
                        }
                    }
                
                }
            } 
       
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        
      return "Success";
   }
}
