package io.mosip.selfregistration.util;

import io.mosip.kernel.core.util.HMACUtils2;
import io.mosip.kernel.core.logger.spi.Logger;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.math.BigInteger;
import java.security.NoSuchAlgorithmException;

@Component
public class TokenIDGenerator {

    @Value("${mosip.selfreg.tokenid.uin.salt}")
    private String uinSalt;

    @Value("${mosip.kernel.tokenid.length}")
    private int tokenIDLength;

    @Value("${mosip.selfreg.tokenid.partnercode.salt}")
    private String partnerCodeSalt;

    @Value("${mosip.selfreg.tokenid.partnercode}")
    private String partnerCode;

     private Logger logger = SelfRegistrationLogger.getLogger(TokenIDGenerator.class);

    public String generateTokenID(String uin) throws Exception {
        logger.info("uin: {}", uin);
        
        logger.info("uinSalt: {}", uinSalt);
        logger.info("partnerCodeSalt: {}", partnerCodeSalt);
        logger.info("partnerCode: {}", partnerCode);
        
        String uinHash = HMACUtils2.digestAsPlainText((uin + uinSalt).getBytes());
        String intermidateHash = HMACUtils2.digestAsPlainText((partnerCodeSalt + "mpartner-default-auth" + uinHash).getBytes());
        String idToken = new BigInteger(intermidateHash.getBytes()).toString().substring(0, tokenIDLength);
        
        logger.info("uinHash: {}", uinHash);
        logger.info("intermidateHash: {}", intermidateHash);
        logger.info("idToken: {}", idToken);

        String idTokenHash = HMACUtils2.digestAsPlainText((idToken + uinSalt).getBytes());
        String hash = HMACUtils2.digestAsPlainText((partnerCodeSalt + partnerCode + idTokenHash).getBytes());
        String token = new BigInteger(hash.getBytes()).toString().substring(0, tokenIDLength);

        logger.info("idTokenHash: {}", idTokenHash);
        logger.info("hash: {}", hash);
        logger.info("token: {}", token);
        return token;
    }

}
