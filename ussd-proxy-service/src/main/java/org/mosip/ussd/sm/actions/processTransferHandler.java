package org.mosip.ussd.sm.actions;

import org.mosip.ussd.entity.Partner;
import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;

import org.springframework.batch.core.JobExecution;
import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.JobParametersInvalidException;

import org.springframework.batch.core.repository.JobExecutionAlreadyRunningException;
import org.springframework.batch.core.repository.JobInstanceAlreadyCompleteException;
import org.springframework.batch.core.repository.JobRestartException;


public class processTransferHandler implements SMAction{

   
    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {
       
        String phoneNo = context.getSessionManager().get("mobileNo");
        String partnerId = context.getSessionManager().get("partnerId");
        String applicationId = context.getSessionManager().get("applicationId");

        String credentialId = cmdText;
        
        Partner partner = context.getConfig().getPartnerService().getPartner(partnerId);
        
        JobParameters params = new JobParametersBuilder()
        .addString("sessionId", sessionId)
        .addString("partnerId", partnerId)
        .addString("partnerUrl", partner.getPartnerUrl())
        .addString("partnerKey", partner.getPartnerKey())
        .addString("applicationId", applicationId)
        .addLong("useCredsAPI", 1L)
        .addLong("onlyDownload",0L)
        .addString("baseUrl", context.getConfig().getResidentAPIHelper().getBaseUrl())
        .addString("residentId",phoneNo)
        .addString("credentialId",credentialId)
        .toJobParameters();
        try {
            JobExecution exec = context.getConfig().getJobLauncher().run(context.getConfig().getJob(), params);
            exec.getId().toString();
        } catch (JobExecutionAlreadyRunningException | JobRestartException | JobInstanceAlreadyCompleteException
                | JobParametersInvalidException e) {
            
            e.printStackTrace();
        }
    
        
        return null;
    }
}
