package org.mosip.ussd.storage;

import org.springframework.stereotype.Repository;
import org.springframework.data.jpa.repository.JpaRepository;

import org.mosip.ussd.entity.UssdSessionValue;
@Repository
public interface SessionValuesRepository extends JpaRepository<UssdSessionValue, Long>{
    
}
