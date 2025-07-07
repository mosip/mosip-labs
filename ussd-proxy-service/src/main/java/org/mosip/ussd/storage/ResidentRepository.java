package org.mosip.ussd.storage;

import javax.transaction.Transactional;

import org.mosip.ussd.entity.Resident;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
@Transactional
public interface ResidentRepository extends JpaRepository<Resident, String> {

    @Modifying
    @Query("update Resident r set r.prefLang = :prefLang  where r.Id = :mobileNo")
    int updateResidentLangCode(@Param("mobileNo") String mobileNo, @Param("prefLang") String lang);

    @Modifying
    @Query("update Resident r set r.VID = :vid where r.Id = :mobileNo")
    int updateResidentUIN(@Param("mobileNo") String mobileNo, @Param("vid") String vid);
}

