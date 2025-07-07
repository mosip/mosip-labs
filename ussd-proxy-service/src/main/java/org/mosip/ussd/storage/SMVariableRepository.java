package org.mosip.ussd.storage;

import org.mosip.ussd.entity.SMVariables;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
@Transactional
public interface SMVariableRepository extends JpaRepository<SMVariables, Long>{
   /*Update value by Id */
    @Modifying
    @Query("update SMVariables r set r.value = :value  where r.Id = :Id")
    int updateVarValaue(@Param("Id") Long id,  @Param("value") String value);

   
}
