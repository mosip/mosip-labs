package org.mosip.ussd.storage;

import org.mosip.ussd.entity.StateMachineContext;
import org.springframework.data.jpa.repository.JpaRepository;

public interface StateMachineContextRepository extends JpaRepository<StateMachineContext, String> {
    
}
