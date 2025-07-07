package org.mosip.ussd.sm.actions;
// import org.mosip.ussd.IdServiceProvider.APICallback;
import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;

public class generateFakeVidHandler implements SMAction {
   

    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {
      
        return "VID12345";
        // boolean validate = true;
        // if ( validate ) {
        //     return "VID12345";
        // }
        // else {
        //     return "UIN is not valid";
        // }
    }
    
}
