package org.mosip.ussd.entity;

import java.io.Serializable;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;

import org.hibernate.annotations.Immutable;
//import org.springframework.data.redis.core.RedisHash;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name="Partners")
@Getter
@Setter
@NoArgsConstructor
//@Immutable
//@RedisHash("Partner")
public class Partner implements Serializable {
    @Id
    @Column(name="Id")
    private String id;
    @Column(name="partnerUrl")
    private String partnerUrl;  
    @Column(name="partnerKey")
    private String partnerKey;  
    
    public Partner(String id, String url, String key){
        this.id = id;
        partnerUrl = url;
        partnerKey = key;
    }  
}
