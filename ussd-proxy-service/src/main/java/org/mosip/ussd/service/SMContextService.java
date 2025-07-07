package org.mosip.ussd.service;

import java.util.List;
import java.util.Optional;


import org.mosip.ussd.entity.SMPrevState;
import org.mosip.ussd.entity.StateMachineContext;
import org.mosip.ussd.sm.models.SMContext;
import org.mosip.ussd.storage.SMPrevStateRepository;
import org.mosip.ussd.storage.SMVariableRepository;
import org.mosip.ussd.storage.StateMachineContextRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Example;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

@Service
public class SMContextService {
    
    @Autowired
    StateMachineContextRepository smContextRepository;

    @Autowired
    SMPrevStateRepository smPrevStateRepository;
    @Autowired 
    SMVariableRepository variableRepository;
  //  @Autowired
  //  CredentialClaimsService credentialClaimsService;
  //  @Autowired
  //  CredentialService credentialService;
  //  @Autowired
  //  PartnerService partnerService;
  //  @Autowired
  //  ResidentService residentService;

    /*
     * When service is restarted clear all old data
     */
    public void cleanUp(){
        variableRepository.deleteAll();
        smPrevStateRepository.deleteAll();
    }
    void setupServices(SMContext smc){
      //  smc.setCredentialClaimsService(credentialClaimsService);
      //  smc.setCredentialService(credentialService);
      //  smc.setPartnerService(partnerService);
      //  smc.setResidentService(residentService);
    }
    public SMContext getContext(String sessionId){
        
        SMContext smc = SMContext.create(this,variableRepository,sessionId);
        Optional<StateMachineContext> ret =  smContextRepository.findById(sessionId);
        if(ret.isPresent()){
            StateMachineContext context =  ret.get();
            smc.setCurrentStateName(context.getCurrentStateName());
            smc.setCurTransitionId(context.getCurrentTransitionId());
            smc.setPrevTransitionId(context.getPrevTransitionId());     
        }
        setupServices(smc);
        return smc;
    }
    public void saveContext(SMContext context){
        StateMachineContext smContext = new StateMachineContext();
        smContext.setId(context.getSessionId());
        smContext.setCurrentStateName(context.getCurrentStateName());
        smContext.setCurrentTransitionId(context.getCurTransitionId());
        smContext.setPrevTransitionId(context.getPrevTransitionId());
        try{
            smContextRepository.deleteById(context.getSessionId());
        }catch(Exception e){

        }
        smContextRepository.saveAndFlush(smContext);
    }
    public List< SMPrevState> loadPrevStates(String sessionId){

        SMPrevState prevState = new SMPrevState();
        prevState.setSessionId(sessionId);
        Example<SMPrevState> example = Example.of(prevState);     
      
       return smPrevStateRepository.findAll(example,Sort.by(Sort.Direction.DESC,"seqNo"));
    }
    public SMPrevState pushState(String sessionId, String stateName){
        SMPrevState state = new SMPrevState();
        
       Long nextNo = smPrevStateRepository.getNexSeqNo(sessionId);
        state.setSeqNo(nextNo);
        state.setSessionId(sessionId);
        state.setPrevStateName(stateName);
        return smPrevStateRepository.saveAndFlush(state);

    }
    public void deletePrevState(Long id){
        smPrevStateRepository.deleteById(id);
    }

}
