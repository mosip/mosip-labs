package io.mosip.selfregistration.entity;

import lombok.Data;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;
import java.time.LocalDateTime;

/**
 * The SelfRegistrationEntity.
 *
 */
@Data
@Entity
@Table(name = "self_registration")
public class SelfRegistrationEntity {

    /** The request id. */
    @Id
    @Column(name = "rid", nullable = false)
    private String rid;

    @Column(name = "name", nullable = false)
    private String name;

    @Column(name = "dob", nullable = false)
    private String dob;

    @Column(name = "gender", nullable = false)
    private String gender;

    @Column(name = "phone", nullable = false)
    private String phone;

    @Column(name = "email_id", nullable = false)
    private String emailId;

    @Column(name = "address", nullable = true)
    private String address;

    @Column(name = "id_type", nullable = true)
    private String idType;

    @Column(name = "id_number", nullable = true)
    private String idNumber;

    @Column(name = "issued_on", nullable = true)
    private LocalDateTime issuedOn;

    @Column(name = "expires_on", nullable = true)
    private LocalDateTime expiresOn;

    /** The biometric data. */
    @Column(name = "bio_data", nullable = false)
    private byte[] biometricData;

    @Column(name = "lang_code", nullable = false)
    private String langCode;

    @Column(name = "uin", nullable = true)
    private String uin;

    /** The status code. */
    @Column(name = "status", nullable = false)
    private String status;

    /** The created by. */
    @Column(name = "cr_by")
    private String createdBy="SYSTEM";

    /** The create date time. */
    @Column(name = "cr_dtimes", updatable = false)

    private LocalDateTime createDateTime;

    /** The updated by. */
    @Column(name = "upd_by")
    private String updatedBy="MOSIP_SYSTEM";

    /** The update date time. */
    @Column(name = "upd_dtimes")
    private LocalDateTime updateDateTime;

    @Column(name = "token_id", nullable = true)
    private String tokenId;
}
