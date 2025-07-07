package org.mosip.ussd.sm.actions;

import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;
import org.mosip.ussd.util.Util;

import okhttp3.*;
import java.io.IOException;


public class lockUnlockUINHandler implements SMAction {
    
    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {
        
        try {
            String uin = context.getSessionManager().get("uin");
            if(uin == null || uin.equals("")){
                uin = cmdText;
                context.getSessionManager().put("uin",uin);
            }

            OkHttpClient client = new OkHttpClient();
            MediaType mediaType = MediaType.parse("application/json");
            RequestBody body = RequestBody.create(mediaType, "{\n  \"id\": \"mosip.resident.auth.lock.unlock\",\n  \"version\": \"1.0\",\n  \"requesttime\": \"2022-05-07T08:26:17.944Z\",\n  \"request\": {\n    \"authTypes\": [\n      {\n        \"authType\": \"demo\",\n        \"authSubType\": null,\n        \"locked\": false,\n        \"unlockForSeconds\": 120\n      },\n      {\n        \"authType\": \"bio\",\n        \"authSubType\": \"FACE\",\n        \"locked\": true,\n        \"unlockForSeconds\": null\n      },\n      {\n        \"authType\": \"otp\",\n        \"authSubType\": \"email\",\n        \"locked\": false,\n        \"unlockForSeconds\": null\n      }\n    ]\n  }\n}");
            
            StringBuilder tempURL = new StringBuilder();
            tempURL.append(context.getConfig().getProps().get("stoplightBaseUrl"));
            // tempURL.append("93015861");
            tempURL.append(uin);
            tempURL.append(Util.LOCK_UNLOCK);

            Request request = new Request.Builder()
                    .url(tempURL.toString())
                    .post(body)
                    .addHeader("Content-Type", "application/json")
                    .addHeader("Accept", "application/json")
                    .build();

            Response response = client.newCall(request).execute();
            
            System.out.println(response.body().string());

        } catch (IOException e) {
            // Handle IOException (e.g., network issues, invalid URL, etc.)
            e.printStackTrace();
        } catch (Exception e) {
            // Handle other exceptions
            e.printStackTrace();
        }

        return null;
    }
}
