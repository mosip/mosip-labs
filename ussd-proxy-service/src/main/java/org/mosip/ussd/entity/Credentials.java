package org.mosip.ussd.entity;
import java.io.Serializable;
import java.time.LocalDateTime;
import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.Table;

import javax.persistence.Id;
import javax.persistence.Lob;


import org.hibernate.annotations.CreationTimestamp;

import org.hibernate.annotations.UpdateTimestamp;
//import org.springframework.data.redis.core.RedisHash;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name="Credentials")
@Getter
@Setter
@NoArgsConstructor
//@Immutable
//@RedisHash("Credentials")
public class Credentials  implements Serializable{
    
    @Id
    @GeneratedValue
    @Column(name = "Id")
    private Long id;

    @Column(name="residentId")
    private String residentId;  //Could be Mobile No

    @Column(name="credName")
    private String name;
    @Lob 
    @Column(name="Content")
    private String content;
    @Column(name="createdAt")
    @CreationTimestamp
    private LocalDateTime createdAt;     //creation timestamp
    @Column(name="updatedAt")
    @UpdateTimestamp
    private LocalDateTime updateAt;
}
