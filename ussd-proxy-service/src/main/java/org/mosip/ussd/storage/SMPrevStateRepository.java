package org.mosip.ussd.storage;

import org.mosip.ussd.entity.SMPrevState;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface SMPrevStateRepository extends JpaRepository<SMPrevState, Long>  {

  // "select max(seqNo) from PrevStates ps where  ps.sessionId = :sessionId")
    
   @Query(value = "select max(seqNo)+1 from SMPrevState where sessionId = :sessionId")
    public Long getNexSeqNo(@Param("sessionId") String sessionId);
        
}
