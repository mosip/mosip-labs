package org.mosip.ussd.sm.utils;

import java.util.List;
import java.util.Stack;

import org.mosip.ussd.entity.SMPrevState;
import org.mosip.ussd.service.SMContextService;

public class SmStack {
    SMContextService contextService;
    Stack<SMPrevState> pendingStates;
    String sessionId;

    public SmStack(SMContextService service, String sessionId){
        contextService = service;
        this.sessionId = sessionId;
        load();
    }
    void load(){
        List<SMPrevState>  states =contextService.loadPrevStates(sessionId);
        pendingStates = new Stack<SMPrevState>();
        for(SMPrevState s: states){
            pendingStates.push(s);
        }
    }
    public SMPrevState push(String stateName){
        SMPrevState state =  contextService.pushState(sessionId, stateName);
        pendingStates.push(state);
        return state;
    }
    public SMPrevState pop(){
        SMPrevState state = pendingStates.pop();
        contextService.deletePrevState(state.getId());
        return state;
    }
    public boolean empty(){
        return pendingStates.empty();
    }
    public SMPrevState peek(){
        return pendingStates.peek();
    }
}
