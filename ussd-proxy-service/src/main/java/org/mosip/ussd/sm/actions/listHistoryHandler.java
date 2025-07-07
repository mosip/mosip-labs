package org.mosip.ussd.sm.actions;

import java.util.ArrayList;
import java.util.List;

import org.mosip.ussd.IdServiceProvider.APICallback;
import org.mosip.ussd.IdServiceProvider.models.AuthHistory;
import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;
public class listHistoryHandler implements SMAction {
    Object syncObject;
    List<AuthHistory> hist;
    String err;
    
    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {
    
        String uin = context.getSessionManager().get("uin");
     
        String trId = context.getSessionManager().get("TrId");
        //syncObjects.put(trId,new Object());
        syncObject = new Object();
        context.getConfig().getResidentAPIHelper().requestResidentHistory(uin,"1", cmdText.trim(), trId,new APICallback(){

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
            try {
                syncObject.wait();
            } catch (InterruptedException e) {
                // TODO Auto-generated catch block
                e.printStackTrace();
            }
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
        String retStr ="";
        for(String s: retVal)
            retStr +=  s +"\n";
        
        return retStr;
    }
    
}
