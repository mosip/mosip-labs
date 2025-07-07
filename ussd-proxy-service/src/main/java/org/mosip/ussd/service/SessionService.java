package org.mosip.ussd.service;


import java.util.Optional;

import org.mosip.ussd.entity.UssdSession;
import org.mosip.ussd.entity.UssdSessionValue;
import org.mosip.ussd.storage.SessionRepository;
import org.mosip.ussd.storage.SessionValuesRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.stereotype.Service;

@Service
public class SessionService {
    
    @Autowired
    private SessionRepository sessionRepository;
    @Autowired
    private SessionValuesRepository sessionValueRepository;

    @Modifying
    public UssdSessionValue updateSessionValue(UssdSessionValue value){
        
        sessionValueRepository.deleteById(value.getId());
        return  sessionValueRepository.saveAndFlush (value);

    }
    public UssdSession getSession(String sessionId){
        Optional<UssdSession> session = sessionRepository.findById(sessionId);
   //     assertTrue(session.isPresent());
        if(session.isPresent())
            return session.get();
        else
            return null;
    }
    public UssdSession setSession(UssdSession session){
        UssdSession rec =  sessionRepository.saveAndFlush(session);
       //session.getValues().forEach( (v)->{
       //    v =  updateSessionValue(v);
       // });
        return rec;
    }
    
    public Iterable<UssdSession> getAll(){
        return sessionRepository.findAll();
    }
    
}
