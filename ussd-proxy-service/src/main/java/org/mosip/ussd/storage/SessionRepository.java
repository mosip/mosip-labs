package org.mosip.ussd.storage;
import org.springframework.stereotype.Repository;
import org.mosip.ussd.entity.UssdSession;
import org.springframework.data.jpa.repository.JpaRepository;
//import org.springframework.data.repository.CrudRepository;
@Repository
public interface SessionRepository extends 
//CrudRepository<UssdSession, String> {
JpaRepository<UssdSession, String> {
}


