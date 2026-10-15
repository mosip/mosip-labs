package io.mosip.selfregistration.repositories;

import io.mosip.selfregistration.entity.SelfRegistrationEntity;
import io.mosip.kernel.core.dataaccess.spi.repository.BaseRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;

/**
 * The Interface SelfRegistrationTransactionRepository.
 *
 * */
@Repository
public interface SelfRegistrationRepository extends BaseRepository<SelfRegistrationEntity, String> {

    @Query("FROM SelfRegistrationEntity WHERE rid=?1")
    SelfRegistrationEntity findByRID(String rid);

    Optional<SelfRegistrationEntity> findByStatus(String status);

    @Query("FROM SelfRegistrationEntity s WHERE lower(emailId)=lower(?1) and s.status=?2")
    Optional<SelfRegistrationEntity> findByEmailIdAndStatus(String emailId, String status);
}
