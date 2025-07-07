
package org.mosip.ussd.entity;

import javax.persistence.Column;
import javax.persistence.Entity;

import javax.persistence.Id;
import javax.persistence.Table;

import org.hibernate.annotations.CollectionId;
import org.hibernate.annotations.Immutable;
//import org.springframework.data.redis.core.RedisHash;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name="Residents")
@Getter
@Setter
@NoArgsConstructor
//@Immutable
//@RedisHash("Resident")
public class Resident {

    @Id
    @Column(name="mobileNo")
    private String Id;
    @Column(name="VID")
    private String VID;
    @Column(name="prefLang")
    private String prefLang;
    
    public Resident( String mobileNo,  String vid){  
        this.VID = vid;
        this.Id = mobileNo;
        this.prefLang = "en";
    }
}