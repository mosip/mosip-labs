package org.mosip.ussd.sm.models;

import java.util.HashMap;
import java.util.List;

import org.mosip.ussd.entity.SMVariables;
import org.mosip.ussd.storage.SMVariableRepository;
import org.springframework.data.domain.Example;



public class SessionManager {
    HashMap<String, SMVariables> variables;
    SMVariableRepository variableRepository;
    String sessionId;

    public SessionManager(SMVariableRepository varRepo, String sessionId){
        variableRepository = varRepo;
        this.sessionId = sessionId;
        loadAll();
       // variables = new HashMap<String,String>();
    }
    public String put(String varName, String varValue){
        SMVariables prevVar = null;
        String prevVal = null;

        if(variables.containsKey(varName)){
            prevVar = variables.get(varName);
            prevVal = prevVar.getValue();
        }
        if(prevVar == null){
            prevVar = new SMVariables();
            prevVar.setSessionId(sessionId);
            prevVar.setKey(varName);
        }
        prevVar.setValue(varValue);
        variables.put(varName, prevVar);
      
        return prevVal;
    }
    public String get(String varName){
        String value  = "";
        if(variables.containsKey(varName)){
            value = variables.get(varName).getValue();
        }
        return value;
    }
    @Override
    public String toString(){
        String r ="\n";
        for(String k: variables.keySet()){
            r = r+ k + "=" + variables.get(k).getValue() +"\n";
        }
        return r;
    }
    public void loadAll(){
        SMVariables var = new SMVariables();
        var.setSessionId(sessionId);
        Example<SMVariables> example = Example.of(var);     
      
       List<SMVariables> vars =  variableRepository.findAll(example);
       variables = new HashMap<>();

       for(SMVariables v: vars){
        variables.put( v.getKey(), v);
       }
    }
    public void saveAll(){
       for(String key: variables.keySet()){
            SMVariables var = variables.get(key);
            if(var.getId() == null)
                variableRepository.saveAndFlush(var);
            else
                variableRepository.updateVarValaue(var.getId(),var.getValue());
       } 
    }
}
