package org.mosip.ussd.sm.actions;

import okhttp3.*;

import org.mosip.ussd.model.AuthResponse;
import org.mosip.ussd.model.AuthStatusResponse;
import org.mosip.ussd.model.AuthType;
import org.mosip.ussd.model.ErrorDetail;
import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;
import org.mosip.ussd.util.Util;

import com.fasterxml.jackson.databind.ObjectMapper;


import java.io.IOException;
import java.util.List;

public class CheckUINStatusHandler implements SMAction {

    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {

        try {
            String uin = context.getSessionManager().get("uin");
            if(uin == null || uin.equals("")){
                uin = cmdText;
                context.getSessionManager().put("uin",uin);
            }
    
            // First API Call: Validate OTP
            OkHttpClient otpClient = new OkHttpClient();
            MediaType otpMediaType = MediaType.parse("application/json");
            RequestBody otpBody = RequestBody.create(otpMediaType, "{\n  \"id\": \"mosip.resident.identity.auth\",\n  \"version\": \"1.0\",\n  \"requesttime\": \"2022-04-07T14:40:42.043Z\",\n  \"request\": {\n    \"individualId\": \"538504179525\",\n    \"transactionID\": \"1234567890\",\n    \"otp\": \"" + cmdText + "\"\n  }\n}");
            
            StringBuilder tempURL = new StringBuilder();
            tempURL.append(context.getConfig().getProps().get("stoplightBaseUrl"));
            // We have been using this hardcoded UIN here as stoplight URLs work only for a defined UIN. 
            // Then we might get a doubt that we can use that UIN as test UIN while working but the issue here is, in this same workflow
            // there are 2 API calls which work with 2 different UINs. Hence we are left with only option to pass that hardcoded UIN while building the API's URL
            tempURL.append("51254318");            
            // tempURL.append(uin);
            tempURL.append(Util.VALIDATE_OTP);

            Request otpRequest = new Request.Builder()
                    .url(tempURL.toString())
                    .post(otpBody)
                    .addHeader("Content-Type", "application/json")
                    .addHeader("Accept", "application/json")
                    .build();

            Response otpResponse = otpClient.newCall(otpRequest).execute();

            if(otpResponse.code() == 200){

                StringBuilder tempURL1 = new StringBuilder();
                tempURL1.append(context.getConfig().getProps().get("stoplightBaseUrl"));
                tempURL1.append("91616815");  
                // tempURL.append(uin);          
                tempURL1.append(Util.UIN_STATUS);

                OkHttpClient uinStatusClient = new OkHttpClient();
                Request uinStatusRequest = new Request.Builder()
                    .url(tempURL1.toString())
                    .get()
                    .addHeader("Accept", "application/json")
                    .build();

                Response uinStatusResponse = uinStatusClient.newCall(uinStatusRequest).execute();
                
                
                String uinStatusResponseStr = uinStatusResponse.body().string();
                
                ObjectMapper objectMapper = new ObjectMapper();
                // Parse JSON using Jackson ObjectMapper
                AuthStatusResponse  uinResponse = objectMapper.readValue(uinStatusResponseStr, AuthStatusResponse.class);
                
                AuthResponse authResponse = uinResponse.getResponse();
                StringBuilder authTypesResponse = new StringBuilder();
                authTypesResponse.append("\nAuth-Type       Locked");
                if( authResponse != null){
                    List<AuthType> allAuthTypes = authResponse.getAuthTypes();
                    for (AuthType authType : allAuthTypes) {
                        String status = authType.isLocked()? "Yes":"No";
                        if(authType.getAuthSubType()!=null && !authType.getAuthSubType().equalsIgnoreCase("null")){
                            authTypesResponse.append("\n");
                            authTypesResponse.append(authType.getAuthSubType());
                            int length = authType.getAuthSubType().length();
                            length = 18 - length;
                            System.out.println(length);
                            while(length>0){
                                System.out.println("Adding Space");
                                authTypesResponse.append(" ");
                                length = length -1 ;
                            }
                            authTypesResponse.append(status);
                        }
                        //18Jan System.out.println("AuthType: " + authType);
                    }   
                }else{
                    List<ErrorDetail> errors = uinResponse.getErrors();
                    for (ErrorDetail Error : errors) {
                        System.out.println("Error : " + Error);
                    }   
                }
                   //authTypes         

                if (uinStatusResponse.code() == 200) {
                    return authTypesResponse.toString();
                }
                else{
                    return "UIN Status Check Failed";
                }
                

            }
            else{
                System.out.println("Wrong OTP entered.");
                return "Wrong OTP entered";
            }

        } catch (IOException e) {
            // Handle IO Exception (e.g., network issues, invalid URL, etc.)
            e.printStackTrace();
            return "Error occurred during API call";
        } catch (Exception e) {
            // Handle other exceptions
            e.printStackTrace();
            return "Unexpected error occurred";
        }
    }
}
