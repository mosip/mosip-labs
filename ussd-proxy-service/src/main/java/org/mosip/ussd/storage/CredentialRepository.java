package org.mosip.ussd.storage;
import org.mosip.ussd.entity.Credentials;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
@Repository
public interface CredentialRepository extends JpaRepository<Credentials, Long>{
    
}
