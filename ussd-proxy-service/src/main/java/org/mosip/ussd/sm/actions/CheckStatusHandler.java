package org.mosip.ussd.sm.actions;

import okhttp3.*;

import org.mosip.ussd.model.CheckStatusError;
import org.mosip.ussd.model.CheckStatusResponse;
import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;
import org.mosip.ussd.util.Util;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.util.List;

public class CheckStatusHandler implements SMAction {

    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {
      
        try {
            String rid = context.getSessionManager().get("rid");
            if(rid == null || rid.equals("")){
                rid = cmdText;
                context.getSessionManager().put("uin",rid);
            }

            // First API Call: Validate OTP
            OkHttpClient otpClient = new OkHttpClient();
            MediaType otpMediaType = MediaType.parse("application/json");
            RequestBody otpBody = RequestBody.create(otpMediaType, "{\n  \"id\": \"mosip.resident.identity.auth\",\n  \"version\": \"1.0\",\n  \"requesttime\": \"2022-04-07T14:40:42.043Z\",\n  \"request\": {\n    \"individualId\": \"538504179525\",\n    \"transactionID\": \"1234567890\",\n    \"otp\": \"" + cmdText + "\"\n  }\n}");
            
            StringBuilder tempURL = new StringBuilder();
            tempURL.append(context.getConfig().getProps().get("stoplightBaseUrl"));
            tempURL.append("51254318");
            // tempURL.append(rid);
            tempURL.append(Util.VALIDATE_OTP);

            Request otpRequest = new Request.Builder()
                    .url(tempURL.toString())
                    .post(otpBody)
                    .addHeader("Content-Type", "application/json")
                    .addHeader("Accept", "application/json")
                    .build();

            Response otpResponse = otpClient.newCall(otpRequest).execute();

            // System.out.println("------------------------------");
            // System.out.println("Here is the OTP response"+otpResponse);
            // System.out.println("------------------------------");

            if (otpResponse.code() == 200) {
                // Second API Call: Check RID Status
                OkHttpClient ridStatusClient = new OkHttpClient();
                MediaType ridStatusMediaType = MediaType.parse("application/json");
                RequestBody ridStatusBody = RequestBody.create(ridStatusMediaType, "{\n  \"id\": \"mosip.resident.checkstatus\",\n  \"version\": \"v1\",\n  \"requestTime\": \"2018-12-09T06:39:04.683Z\",\n  \"request\": {\n    \"individualId\": \"9830872690593682\",\n    \"individualIdType\": \"RID\"\n  }\n}");
                
                StringBuilder tempURL1 = new StringBuilder();
                tempURL1.append(context.getConfig().getProps().get("stoplightBaseUrl"));
                tempURL1.append("120374355");
                // tempURL.append(rid);
                tempURL1.append(Util.RID_STATUS);

                Request ridStatusRequest = new Request.Builder()
                        .url(tempURL1.toString())
                        .post(ridStatusBody)
                        .addHeader("Content-Type", "application/json")
                        .addHeader("Accept", "application/json")
                        .build();

                Response ridStatusResponse = ridStatusClient.newCall(ridStatusRequest).execute();

                if (ridStatusResponse.code() == 200) {

                    ObjectMapper objectMapper = new ObjectMapper();
                    // Parse JSON using Jackson ObjectMapper
                    CheckStatusResponse  CheckStatusResponse = objectMapper.readValue(ridStatusResponse.body().string(), CheckStatusResponse.class);

                    if (CheckStatusResponse != null) {
                        List<CheckStatusError> errors = CheckStatusResponse.getErrors();
                        if (errors != null && !errors.isEmpty()) {
                            System.out.println("Errors:");
                            for (CheckStatusError error : errors) {
                                System.out.println("  ErrorCode: " + error.getErrorCode() + ", ErrorMessage: " + error.getErrorMessage());
                            }
                        } else {
                            if (CheckStatusResponse.getResponse() != null) {
                                String ridStatus = CheckStatusResponse.getResponse().getRidStatus();
                                System.out.println("ridStatus: " + ridStatus);
                            } else {
                                System.out.println("Response is missing the 'response' field.");
                            }
                        }
                    }
                    return "Success";
                } else {
                    return "RID Status Check Failed";
                }
            } else {
                return "Wrong OTP";
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
