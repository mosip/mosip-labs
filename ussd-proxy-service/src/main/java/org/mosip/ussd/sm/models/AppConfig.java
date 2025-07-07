package org.mosip.ussd.sm.models;
import java.util.Map;

import org.mosip.ussd.IdServiceProvider.IDCredsHelper;
import org.mosip.ussd.IdServiceProvider.MOSIPAPIHelper;
import org.mosip.ussd.service.CredentialClaimsService;
import org.mosip.ussd.service.CredentialService;
import org.mosip.ussd.service.PartnerService;
import org.mosip.ussd.service.ResidentService;
import org.mosip.ussd.service.SMContextService;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.launch.JobLauncher;

import lombok.Data;

@Data
public class AppConfig {

    Map<String,String> props;
    String mimotoBaseURL;
    String residentServiceBaseURL;
    
    IDCredsHelper idCredsHelper;
    MOSIPAPIHelper residentAPIHelper;
   
    /*Storage services */
    CredentialClaimsService credentialClaimsService;
    CredentialService credentialService;
    PartnerService partnerService;
    ResidentService residentService;
    SMContextService ctxService;
    
    JobLauncher jobLauncher;
    Job job;
 
    public void Init(Map<String,String> props){
        this.props =props;
        
        idCredsHelper = new IDCredsHelper(props.get("credServiceBaseUrl"));
        residentAPIHelper = new MOSIPAPIHelper(props.get("ResidentAPIBaseUrl"),props.get("appId"),props.get("clientId"),props.get("clientSecret"));
        residentAPIHelper.authApp();
    }
}
