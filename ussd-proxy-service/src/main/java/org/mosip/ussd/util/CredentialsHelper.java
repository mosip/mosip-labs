package org.mosip.ussd.util;
import java.util.ArrayList;


import java.util.List;
import java.util.Optional;

import org.mosip.ussd.IdServiceProvider.APICallback;
import org.mosip.ussd.IdServiceProvider.IDCredsHelper;
import org.mosip.ussd.IdServiceProvider.MOSIPAPIHelper;
import org.mosip.ussd.IdServiceProvider.models.AuthHistory;
import org.mosip.ussd.entity.Credentials;
import org.mosip.ussd.entity.Partner;
import org.mosip.ussd.entity.UssdSession;
import org.mosip.ussd.entity.UssdSessionValue;
import org.mosip.ussd.model.Commands;
import org.mosip.ussd.model.DialogState;
import org.mosip.ussd.service.CredentialService;
import org.mosip.ussd.service.SessionService;
import org.mosip.ussd.storage.PartnerRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.JobParametersInvalidException;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.batch.core.repository.JobExecutionAlreadyRunningException;
import org.springframework.batch.core.repository.JobInstanceAlreadyCompleteException;
import org.springframework.batch.core.repository.JobRestartException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Component;
import org.mosip.ussd.dialog.UssdMenu;



@Component
public class CredentialsHelper {

    private static final Logger logger = LoggerFactory.getLogger(CredentialsHelper.class);
  
 
    @Autowired
    @Qualifier("simpleJobLauncher")
    JobLauncher jobLauncher;
     
    @Autowired
    PartnerRepository partnerRepository;
 
    @Autowired
    CredentialService credentialService;
    
    @Autowired
    Job job;
    MOSIPAPIHelper idProvider;
    IDCredsHelper idCredsProvider;
    Boolean enaleCredsProvider ;
    UssdMenu menu;

    String newvid;
    String err;
    Object syncObject ;
    List<AuthHistory> hist;

    public String getError(){
        return err;
    }
    public CredentialsHelper(){
        enaleCredsProvider =false;
       // syncObjects = new HashMap<String,Object>();
    }
    public void setMenu(UssdMenu m){
        menu = m;
    }
    public void setMode(Boolean enableCredsAPI){
        enaleCredsProvider = enableCredsAPI;
    }
    public void setIdProvider(MOSIPAPIHelper idProvider){
        this.idProvider = idProvider;
    }
    public void setIdCredsProvider( IDCredsHelper provider){
        idCredsProvider  = provider;
        enaleCredsProvider =false;
    }
    public CredentialsHelper(MOSIPAPIHelper idProvider){
        this.idProvider = idProvider;
    }
    public String processListCredentials(UssdSession state,String sessionId, Boolean bIncludeCmd){
        
        List<Credentials> creds = credentialService.getAllCredentials(state.getPhoneNo());
        String [] strCreds  = new String[creds.size()];
        int i=0;
        for(Credentials c: creds){
            String s = c.getId() +" "+ c.getName();
            strCreds[i++] = s;
        }
        return menu.constructMenu("response",  Commands.END, bIncludeCmd,strCreds);
    
    }
    public String processHistoryRequest(String otp,UssdSession state, String sessionId,String cmdText,Boolean bIncludeCmd) throws InterruptedException{

        String uin = state.findValue(Util.ID).getValue();
        String trId = state.findValue(Util.TrId).getValue();
        //syncObjects.put(trId,new Object());
        syncObject = new Object();
        idProvider.requestResidentHistory(uin,"1", otp, trId,new APICallback(){

            @Override
            public void onSuccess(Object param) {
                hist = (List<AuthHistory>) param;
                
                synchronized(syncObject){
                    syncObject.notify();
                }
            }

            @Override
            public void onError(Object param) {
                err = param.toString();
                synchronized(syncObject){
                    syncObject.notify(); 
                }
            }

        });
        synchronized(syncObject){
            syncObject.wait();
        }
        ArrayList<String> authHistory = new ArrayList<String>();
        int c =0;
        for(AuthHistory ah: hist){
        
            String s = ah.partnerName +" "+ ah.date;
            if(c < 5)
                authHistory.add(s);
            else
                break;
            c++;
            
        }
        String[] retVal = new String[authHistory.size() ];
        retVal = authHistory.toArray(retVal);
        return menu.constructMenu("response",  Commands.END, bIncludeCmd,retVal);
        
    }
   public String processRequest(SessionService sessionService, UssdSession state, String sessionId,String cmdText,Boolean bIncludeCmd){
    String ret ="";
    String val ="";
    
    logger.info("processRequest entry");
    
    UssdSessionValue value = state.findValue(Util.STATE);
    if(value == null)
        logger.info("processRequest STATE value==> NULL");
    else
    logger.info("processRequest STATE value <> NULL, state=" + value.getValue());
    
    //value.setUssdSession(state);
    DialogState st = DialogState.valueOf( value.getValue());
    switch(st){

        case GotOtp_DownloadCredentails:
            logger.info("GotOtp");
              //todo: Process Credentials Transfer
              ret =  processCredTransfer(sessionId,state, enaleCredsProvider, true);
              //ret = Util.constructMenu(new String []{"Request for VC Transfer placed"}, Commands.END, bIncludeCmd);
              ret = menu.constructMenu("VCRequest", Commands.END, bIncludeCmd);
          
            break;
        case GotRPPartnerId:
        
            val = cmdText.trim();
            state.addValue(new UssdSessionValue(sessionId,Util.RPPartnerId, val));
            
          //  ret = Util.constructMenu(UssdMenu.RPApplMenu, Commands.CON, bIncludeCmd);
            ret = menu.constructMenu("RPApplMenu", Commands.CON, bIncludeCmd);
          
            value.setValue( DialogState.GotRPApplicationId.toString());
            state.updateValue(value);
           
            value = sessionService.updateSessionValue(value);
            break;
        case GotRPApplicationId:
            val = cmdText.trim();
            state.addValue(new UssdSessionValue(sessionId,Util.RPApplicationId, val));   
            ret =  processCredTransfer(sessionId,state, enaleCredsProvider, false);
            ret = menu.constructMenu("VCRequest", Commands.END, bIncludeCmd);
            
            
            break;
        default:

    }
    return ret;
     
   } 

   String requestId;
   /*
    * bSave = True -> Download and Save credentials
    * bSave = False -> Transfer downloaded credentials
    */
   String processCredTransfer(String sessionId, UssdSession state, Boolean enaleCredsProvider, Boolean bSave){
    
        runCredJob( sessionId,  state, enaleCredsProvider, bSave);
        return "";
   }
   
   public String processVIDRequest(String sessionId, UssdSession state, String vidType) throws InterruptedException{
    
        
        String id = state.findValue(Util.ID).getValue();
        String otp = state.findValue(Util.OTP).getValue();
        String trid = state.findValue(Util.TrId).getValue();
        syncObject = new Object();
        logger.info("processVIDRequest: ID=" +id + ",OTP="+ otp );
        idProvider.requestVID(id,"UIN", trid, otp, vidType, new APICallback(){

            @Override
            public void onSuccess(Object param) {
                newvid = param.toString();
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

        });
        synchronized(syncObject){
            syncObject.wait();
        }
        return newvid;
   }
   public void runCredJob(String sessionId, UssdSession state, Boolean enaleCredsProvider, Boolean bSave){

    String uin = bSave ? state.findValue(Util.ID).getValue() : "";
    String otp = bSave ? state.findValue(Util.OTP).getValue() : "";
    String trId = bSave ? state.findValue(Util.TrId).getValue() :"";

    String partnerId = bSave ? "": state.findValue(Util.RPPartnerId).getValue();
    String applicationId = bSave ? "" : state.findValue(Util.RPApplicationId).getValue();
   
    String url = idProvider.getBaseUrl();
    if(enaleCredsProvider)
        url = idCredsProvider.getBaseUrl();
        
    String partnerUrl ="";
    String partnerKey ="";
    if(!bSave){   
        Optional<Partner> ret = partnerRepository.findById(partnerId);
        if(ret.isPresent()){
            partnerUrl = ret.get().getPartnerUrl();
            partnerKey = ret.get().getPartnerKey();
        } 
    }
    JobParameters params = new JobParametersBuilder()
        .addString("sessionId", sessionId)
        .addString("uin", uin)
        .addString("otp", otp)
        .addString("TrId",trId)
        .addString("partnerId", partnerId)
        .addString("partnerUrl", partnerUrl)
        .addString("partnerKey", partnerKey)
        .addString("applicationId", applicationId)
        .addString("appId", idProvider.getAppId())
        .addString("clientId", idProvider.getClientId())
        .addString("clientSecret", idProvider.getClientSecret())
       
        .addLong("useCredsAPI",( enaleCredsProvider ? 1L: 0L))
        .addLong("onlyDownload",( bSave ? 1L: 0L))
        .addString("baseUrl", url)
        .addString("residentId",state.getPhoneNo())
        .toJobParameters();

    try {
        logger.info("jobLauncher begin");
        jobLauncher.run(job, params);
        logger.info("jobLauncher done");
        

    } catch (JobExecutionAlreadyRunningException | JobRestartException | JobInstanceAlreadyCompleteException
            | JobParametersInvalidException e) {
        logger.error(e.getMessage());
        e.printStackTrace();
    }
   }
}
