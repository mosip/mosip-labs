package org.mosip.ussd.sm.actions;

import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;

import org.springframework.batch.core.JobExecution;
import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.JobParametersInvalidException;

import org.springframework.batch.core.repository.JobExecutionAlreadyRunningException;
import org.springframework.batch.core.repository.JobInstanceAlreadyCompleteException;
import org.springframework.batch.core.repository.JobRestartException;

public class downloadVCHandler implements SMAction{

   
    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {
       
        String retVal = "-1";
        String uin = context.getSessionManager().get("uin");
        String trId = context.getSessionManager().get("TrId");
        String phoneNo = context.getSessionManager().get("mobileNo");
        String otp = cmdText;
        JobParameters params = new JobParametersBuilder()
        .addString("sessionId", sessionId)
        .addString("uin", uin)
        .addString("otp", otp)
        .addString("TrId",trId)
        .addString("appId", context.getConfig().getResidentAPIHelper().getAppId())
        .addString("clientId", context.getConfig().getResidentAPIHelper().getClientId())
        .addString("clientSecret", context.getConfig().getResidentAPIHelper().getClientSecret())
       
        .addLong("useCredsAPI", 1L)
        .addLong("onlyDownload",1L)
        .addString("baseUrl", context.getConfig().getResidentAPIHelper().getBaseUrl())
        .addString("residentId",phoneNo)
        .toJobParameters();
        try {
            JobExecution exec = context.getConfig().getJobLauncher().run(context.getConfig().getJob(), params);
            retVal = exec.getId().toString();
        } catch (JobExecutionAlreadyRunningException | JobRestartException | JobInstanceAlreadyCompleteException
                | JobParametersInvalidException e) {
            
            e.printStackTrace();
        }
   
     
        return null;
    }
}
