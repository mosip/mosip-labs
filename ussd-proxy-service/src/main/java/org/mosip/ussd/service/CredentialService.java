package org.mosip.ussd.service;

import java.util.List;
import java.util.Optional;


import org.mosip.ussd.entity.Credentials;
import org.mosip.ussd.storage.CredentialRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Example;
import org.springframework.stereotype.Service;

@Service
public class CredentialService {
    @Autowired
    CredentialRepository credentialRepository;
    
    private static final Logger logger = LoggerFactory.getLogger(CredentialService.class);
   
   public  Credentials addCredential(Credentials credential){
    
    logger.info("Id="+credential.getResidentId());

    return  credentialRepository.saveAndFlush(credential);

   }
   public Credentials getCredential(Long id){
       
    Optional<Credentials> ret  = credentialRepository.findById(id);
    if(ret.isPresent())
        return ret.get();
    else
        return null;
        
    }
    public List<Credentials> getAllCredentials(String residentId){
        Credentials cred = new Credentials();
        cred.setResidentId(residentId);
        Example<Credentials> example = Example.of(cred);     
        return credentialRepository.findAll(example);

    }   
}
