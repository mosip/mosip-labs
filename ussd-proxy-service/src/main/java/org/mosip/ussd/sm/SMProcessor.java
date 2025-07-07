package org.mosip.ussd.sm;

import java.io.IOException;
import java.io.InputStream;
import java.util.Map;

import com.fasterxml.jackson.core.JsonParseException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.mosip.ussd.dialog.UssdMenu;
import org.mosip.ussd.entity.Resident;
import org.mosip.ussd.sm.models.AppConfig;
import org.mosip.ussd.sm.models.SMCondition;
import org.mosip.ussd.sm.models.SMContext;
import org.mosip.ussd.sm.models.SMStateModel;
import org.mosip.ussd.sm.models.SMTransistionModel;

import org.mosip.ussd.sm.models.StateMachineModel;
import org.mosip.ussd.sm.models.StateMachinesModel;

import org.mosip.ussd.model.Commands;
import org.mosip.ussd.service.SMContextService;
import org.mosip.ussd.sm.utils.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


/*
 * StateMachine Processor
 * Load SM from Json and parse, construct models
 */
public class SMProcessor {

    private static final Logger logger = LoggerFactory.getLogger(SMProcessor.class);
   
    ObjectMapper objectMapper = new ObjectMapper();
    //List<StateMachineModel> listSMs =null;
    StateMachinesModel sms ;
    StateMachineModel curStateMachineModel;

    SMContextService contextService;
   // SMStateModel curState;

    UssdMenu menuHelper ;
    SMContext context;
    String langCode = "en";
    AppConfig config;
    String SMJasonFile ;

    public SMContext getContext(){
        return context;
    }
    public SMProcessor(SMContextService cxService){
        contextService = cxService;
    }
    public Boolean Init(Map<String,String> args, AppConfig config){
        Boolean bRet = false;
        try {
            SMJasonFile = args.get("SMJasonFile");
            loadStateMachineModel();
            menuHelper = new UssdMenu();
            menuHelper.loadMenu(langCode);
            this.config = config;
            
        
            bRet = true;
        } catch (IOException e) {
            
            e.printStackTrace();
        }
        return bRet;
    } 
    StateMachinesModel loadStateMachineModel() throws JsonParseException, JsonMappingException, IOException{
        String filePath = SMJasonFile;
		InputStream in = getClass().getResourceAsStream(filePath);
		if(in != null){
            
            objectMapper.configure(DeserializationFeature.FAIL_ON_MISSING_CREATOR_PROPERTIES, false);
            sms =  objectMapper.readValue(in, StateMachinesModel.class);	
            in.close();
           
        }
        return sms;
    }
    public void load(String sessionId){
        
        context = contextService.getContext(sessionId);
        context.setConfig(config);
        //SA: load resident config to sessionManager
        Resident res =config.getResidentService().getResident(context.getSessionManager().get("mobileNo"));
        if(res != null){
            context.getSessionManager().put("uin",res.getVID());
            context.getSessionManager().put("lang",res.getPrefLang());
        }
        logger.info(context.getSessionManager().toString());
    }
    void updateContext(){
        String id = context.getCurTransitionId();
        if(id != null && !id.equals(""))
            context.setCurTransition(getTransitionById(id));
        id = context.getPrevTransitionId();
        if(id != null && !id.equals(""))
            context.setPrevTransition(getTransitionById(id));
    }
    public SMStateModel getEntryState(StateMachineModel sm){
       
        for(SMStateModel state: sm.getStates()){
            if(state.getPosition().equals(Constants.POS_ENTRY))
                return state;
        }
        return null;
    }

    public StateMachineModel getStateMachine(String serviceCode){
        for(StateMachineModel sm: sms.getMachines()){
            if(sm.getServicecode().equals(serviceCode) ){
                return sm;
            }
        }
        return null;
    }
    String execClass(String className, SMContext context,String cmdText, String sessionId){
        String result = "";
        try {
            final Class<?> c = Class.forName(className);
            SMAction action = (SMAction)c.getDeclaredConstructor().newInstance();
            result = action.execute(context,cmdText, sessionId);
            
        } catch (Exception  e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        } 
        return result;
    }
    SMStateModel getStateByName(String name){
        for(SMStateModel smsm: curStateMachineModel.getStates()){
            if(smsm.getName().equals(name))
                return smsm;
        }
        return null;
    }
    SMTransistionModel getTransitionById(String id){
        for(SMTransistionModel tm: curStateMachineModel.getTransitions()){
            if(tm.getId().equals(id))
                return tm;
        }
        return null;
    }
    String getNextStateNameCaseInput(SMContext context,String cmdText, SMTransistionModel smtm){
        String nextStateName = null;
        boolean bInputMatch = false;
        if(smtm.getFrom().equals(context.getCurrentStateName()) ){
            if(smtm.getEvttype().equals(Constants.EVT_TYPE_INPUT) && smtm.getEvtvalue().equals(cmdText) ){
                nextStateName = smtm.getTo();
                bInputMatch = true;
            }
            else
            if(smtm.getEvttype().equals(Constants.EVT_TYPE_AUTO))
                bInputMatch = true;

            Boolean bCondition = EvalCondition(smtm.getCondition());
            if(bCondition == null)
                return nextStateName;
            if(bInputMatch && bCondition){
                nextStateName = smtm.getCondition().getToState();
                context.getPendingStates().push( smtm.getTo());
            }

        }
        return nextStateName;
    }
    String getNextStateNameCaseTagCondtion(SMContext context,String cmdText, SMTransistionModel smtm){
        String nextStateName = null;
        if(smtm.getFrom().equals(context.getCurrentStateName()) && smtm.getEvttype().equals(Constants.EVT_TYPE_AUTO) ){
            SMCondition cndnVar = smtm.getCondition();
            if(cndnVar != null && cndnVar.getVariable() != null && cndnVar.getVariable().getVarName().equals("tag") ){
                
                SMTransistionModel prevTrans = context.getPrevTransition();
                if(prevTrans != null) {
                    if(prevTrans.getTag().equals(cndnVar.getVariable().getVarValue())){
                        nextStateName = cndnVar.getVariable().getVarValue();
                        
                    }
                }
                
            }
        }
        return nextStateName;
    }
    Boolean EvalCondition( SMCondition cndnVar){
        Boolean bCondition = null;
        if(cndnVar != null && cndnVar.getVariable() != null ){
         
            String varVal = context.getSessionManager().get( cndnVar.getVariable().getVarName());
            String cndnVal = cndnVar.getVariable().getVarValue();
            if(cndnVar.getOperation().equals("null"))
                bCondition = (cndnVal == null);
            else
            if(cndnVar.getOperation().equals("="))
                bCondition = ( cndnVal == varVal);
            else
            if(cndnVar.getOperation().equals("<>"))
                    bCondition = ( cndnVal != varVal);
                                   
        }
        return bCondition;
     
    }
    String getNextStateNameCaseVarCondtion(SMContext context,String cmdText, SMTransistionModel smtm){
        String nextStateName = null;
        if(smtm.getEvttype().equals(Constants.EVT_TYPE_AUTO) ){
            SMCondition cndnVar = smtm.getCondition();
            if(cndnVar != null  ){
                Boolean bCondition = false;

                String varVal = context.getSessionManager().get( cndnVar.getVariable().getVarName());
                String cndnVal = cndnVar.getVariable().getVarValue();
                if(cndnVar.getOperation().equals("null"))
                    bCondition = (cndnVal == null);
                else
                if(cndnVar.getOperation().equals("="))
                    bCondition = ( cndnVal == varVal);
                else
                if(cndnVar.getOperation().equals("<>"))
                        bCondition = ( cndnVal != varVal);
                        
                if(bCondition){
                    nextStateName = cndnVar.getToState();
                    context.getPendingStates().push(smtm.getTo());
                }                    
            }
                
        }
        
        return nextStateName;
    }
  
    SMStateModel getNextState(SMContext context,String cmdText){
        SMStateModel nextState = null;
        SMTransistionModel curTr = null;
        System.out.println("Context=" + context.toString());
        context.setPrevTransition(context.getCurTransition());

        if(!context.getPendingStates().empty()){
            String stateName = context.getPendingStates().pop().getPrevStateName();
            nextState = getStateByName(stateName);
            context.setCurrentStateName(nextState.getName());
            return nextState;
        }
        String nextStateName = null;
        for(SMTransistionModel smtm: curStateMachineModel.getTransitions()){
            curTr = smtm;
            nextStateName = getNextStateNameCaseInput( context, cmdText, smtm);
            
            //if(nextStateName != null){
            //    System.out.println("getNextStateNameCaseTagCondition == NULL " + smtm.getId());
            //    nextStateName =  getNextStateNameCaseVarCondtion( context, cmdText,  smtm);
              //  if(nextStateName != null)
              //      context.getPendingStates().push(smtm.getFrom());

            //}
          
            if(nextStateName == null){
                System.out.println("getNextStateNameCaseInput == NULL " + smtm.getId());
                nextStateName = getNextStateNameCaseTagCondtion(context,cmdText, smtm );
              //  if(nextStateName != null)
              //      context.getPendingStates().push(curTr.getFrom());

            }

            
            if(nextStateName != null){
                System.out.println("Final !=NULL "+ nextStateName+ ",Id="+ smtm.getId());
                if(smtm.getSaveto() != null && !smtm.getSaveto().isEmpty())
                    context.getSessionManager().put(smtm.getSaveto(),cmdText);    
                break;
            }
        }
        if(nextStateName == null){
            for(SMTransistionModel smtm: curStateMachineModel.getTransitions()){
                curTr = smtm;
                System.out.println("getNextStateNameTagCondition == NULL "+ smtm.getId());
                if(smtm.getEvttype().equals(Constants.EVT_TYPE_AUTO) &&
                    smtm.getFrom().equals(context.getCurrentStateName()) ){
                        nextStateName = smtm.getTo();
                        if(smtm.getSaveto() != null && !smtm.getSaveto().isEmpty())
                            context.getSessionManager().put(smtm.getSaveto(),cmdText);  
                    logger.info("nextstate="+ nextStateName +  ",cmdText="+ cmdText+", saveTo:"+ smtm.getSaveto());  
                        break;
                }
            }
        }
        if(nextStateName == null)
            System.out.println("NO match found - State NULL");
        
        nextState = getStateByName(nextStateName);
        context.setPrevTransition( context.getCurTransition());
        context.setCurTransition(curTr);
        return nextState;
    }
   
    String execState(SMContext context, SMStateModel smm, String cmdText, String sessionId){
  
        //Save input text to specifid variable
        if(smm.getSaveto() != null && !smm.getSaveto().isEmpty())
            context.getSessionManager().put( smm.getSaveto(), cmdText);

        String result = execClass( smm.getHandler(),context, cmdText, sessionId);
        Commands cmd = Commands.CON;
        if(smm.getPosition().equals(Constants.POS_END))
            cmd = Commands.END;
        if(result == null || result.isEmpty())    
            result = menuHelper.constructMenu(smm.getMenu(), cmd, true);
        else
            result = menuHelper.constructMenu(smm.getMenu(), cmd, true, result);
       
        return result;
    }
    public String execute(String cmdText,String serviceCode, String sessionId){
      
        StateMachineModel sm = getStateMachine(serviceCode);
        String result = null;
        curStateMachineModel = sm;
        SMStateModel smState;
        logger.info(context.getSessionManager().toString());
        String l = context.getSessionManager().get("lang");
        if(l != null && !l.isEmpty())
            langCode = l;
            
        menuHelper.loadMenu(langCode);
        
        updateContext();
        logger.info("cmdText=" + cmdText);
        
        if(cmdText == null || cmdText.isEmpty()){
            smState = getEntryState(sm);    
        }
        else{
            smState = getNextState(context,cmdText); 
        }
        if(smState == null){
            logger.error("Failed to get next state");
            result  = menuHelper.constructMenu("errorMessage", Commands.END, true);
            return result;
        }
        logger.info("smState name="+ smState.getName());
        
        context.setCurrentStateName(smState.getName());

     //   logger.info("prev-tr=" + ((context.getPrevTransition() == null) ? "null": context.getPrevTransition().getId()));
     //   logger.info("cur-tr=" + ((context.getCurTransition() == null) ? "null": context.getCurTransition().getId()));
        
        result = execState(context,smState, cmdText, sessionId);
       // System.out.println(result);
        return result;
    }
    
}
