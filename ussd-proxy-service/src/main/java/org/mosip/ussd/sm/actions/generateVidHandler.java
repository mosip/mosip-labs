package org.mosip.ussd.sm.actions;
import org.mosip.ussd.IdServiceProvider.APICallback;
import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;

public class generateVidHandler implements SMAction {
    Object syncObject ;
    String newVid;
    String err;

    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {
      
        String otp = cmdText.trim();
        String uin  = context.getSessionManager().get("uin");
        //call API to generate VID for the UIN
        String trid = context.getSessionManager().get("TrId");
        syncObject = new Object();
      
        context.getConfig().getResidentAPIHelper().requestVID(uin,"UIN", trid, otp, "Temporary", new APICallback(){

            @Override
            public void onSuccess(Object param) {
                newVid = param.toString();
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
            try {
                syncObject.wait();
            } catch (InterruptedException e) {
              
                e.printStackTrace();
            }
        }
        return newVid;
    }
    
}
