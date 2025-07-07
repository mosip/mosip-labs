package org.mosip.ussd.sm.models;


import org.mosip.ussd.service.SMContextService;
import org.mosip.ussd.sm.utils.SmStack;
import org.mosip.ussd.storage.SMVariableRepository;

import lombok.Data;

/*
 * Context class to pass parameters to Actions
 * We need to persist this 
 * Hence instead of objets, save names
 * Session Variables - could be persisted in db/redis
 * Pending States - list of forward states to be executed till stack is empty
 */ 
@Data
public class SMContext {
    String sessionId;
    String curTransitionId;
    String prevTransitionId;

    SessionManager sessionManager;
    SMTransistionModel curTransition;
    SMTransistionModel prevTransition;
    SmStack pendingStates;
    SMContextService contextService;
    String currentStateName;
    AppConfig config;

    public static SMContext create(SMContextService service,SMVariableRepository varRepo,String sessionId){
        SMContext ctx = new SMContext(service, varRepo,sessionId);
        return ctx;
    }
    protected SMContext(SMContextService service,SMVariableRepository varRepo, String sessionId){
        this.sessionId = sessionId;
        sessionManager = new SessionManager(varRepo,sessionId);  
       // pendingStates = new Stack<String>();  
       pendingStates = new SmStack( service, sessionId);
       contextService = service;
    }
   
    public void save(){
        if(curTransition != null)
            curTransitionId = curTransition.getId();
        if(prevTransition != null)
            prevTransitionId = prevTransition.getId();

        contextService.saveContext(this);
        sessionManager.saveAll();
    }
    @Override
    public String toString(){
       return("sessionId=" + sessionId + "\nsession Vars="+ sessionManager.toString() + "\n"
                +( curTransition != null ? curTransition.getId() :" ")
                + ",cur transition=" + ( curTransition != null ? curTransition.getFrom(): "") 
                +"," + ( curTransition != null ? curTransition.getTo() :"")
                + "\npending-state=" + (pendingStates.empty() ? "Empty": pendingStates.peek()));

    }
}
