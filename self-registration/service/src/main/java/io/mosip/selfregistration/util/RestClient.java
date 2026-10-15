package io.mosip.selfregistration.util;

import com.google.gson.Gson;
import io.mosip.kernel.core.util.DateUtils;
import io.mosip.kernel.core.util.StringUtils;
import io.mosip.kernel.core.util.TokenHandlerUtil;
import io.mosip.selfregistration.constant.ApiName;
import io.mosip.selfregistration.dto.Metadata;
import io.mosip.selfregistration.dto.SecretKeyRequest;
import io.mosip.selfregistration.dto.TokenRequestDTO;
import io.mosip.selfregistration.exception.ApisResourceAccessException;
import io.mosip.kernel.core.logger.spi.Logger;
import org.apache.commons.lang3.exception.ExceptionUtils;
import org.apache.http.Header;
import org.apache.http.HttpResponse;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.util.EntityUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.core.env.Environment;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponents;
import org.springframework.web.util.UriComponentsBuilder;

import java.io.IOException;
import java.util.Iterator;
import java.util.List;


/**
 *
 * @author Dhanendra
 *
 */
@Component
public class RestClient {

    /** The environment. */
    @Autowired
    private Environment environment;

    @Autowired
//    @Qualifier("selfTokenRestTemplate")
    private RestTemplate restTemplate;

    /** The Constant AUTHORIZATION. */
    private static final String AUTHORIZATION = "Authorization=";

    private Logger logger = SelfRegistrationLogger.getLogger(RestClient.class);


    /**
     * Post api.
     *
     * @param <T>             the generic type
     * @param apiName         the api name
     * @param pathsegments    the pathsegments
     * @param queryParamName  the query param name
     * @param queryParamValue the query param value
     * @param mediaType       the media type
     * @param requestType     the request type
     * @param responseClass   the response class
     * @return the t
     * @throws Exception
     */
    @SuppressWarnings("unchecked")
    public <T> T postApi(ApiName apiName, List<String> pathsegments, String queryParamName, String queryParamValue,
                         MediaType mediaType, Object requestType, Class<?> responseClass) throws Exception {
        T result = null;
        try {
            String apiHostIpPort = environment.getProperty(apiName.name());
            UriComponentsBuilder builder = null;
            if (apiHostIpPort != null)
                builder = UriComponentsBuilder.fromUriString(apiHostIpPort);
            if (builder != null) {

                if (!((pathsegments == null) || (pathsegments.isEmpty()))) {
                    for (String segment : pathsegments) {
                        if (!((segment == null) || (("").equals(segment)))) {
                            builder.pathSegment(segment);
                        }
                    }

                }
                if (!((queryParamName == null) || (("").equals(queryParamName)))) {
                    String[] queryParamNameArr = queryParamName.split(",");
                    String[] queryParamValueArr = queryParamValue.split(",");

                    for (int i = 0; i < queryParamNameArr.length; i++) {
                        builder.queryParam(queryParamNameArr[i], queryParamValueArr[i]);
                    }
                }
                logger.info("RestApiClient::postApi()::entry uri : {}",apiHostIpPort);
                result = (T) restTemplate.postForObject(builder.toUriString(), setRequestHeader(requestType, mediaType),
                        responseClass);
            }
        } catch (Exception e) {
            logger.error(e.getMessage() + ExceptionUtils.getStackTrace(e));
            throw new Exception(e);
        }
        return result;
    }

    /**
     * Gets the api.
     *
     * @param <T>             the generic type
     * @param apiName         the api name
     * @param pathsegments    the pathsegments
     * @param queryParamName  the query param name
     * @param queryParamValue the query param value
     * @param responseType    the response type
     * @return the api
     * @throws Exception
     */
    @SuppressWarnings("unchecked")
    public <T> T getApi(ApiName apiName, List<String> pathsegments, String queryParamName, String queryParamValue,
                        Class<?> responseType) throws Exception {

        String apiHostIpPort = environment.getProperty(apiName.name());
        T result = null;
        UriComponentsBuilder builder = null;
        UriComponents uriComponents = null;
        if (apiHostIpPort != null) {

            builder = UriComponentsBuilder.fromUriString(apiHostIpPort);
            if (!((pathsegments == null) || (pathsegments.isEmpty()))) {
                for (String segment : pathsegments) {
                    if (!((segment == null) || (("").equals(segment)))) {
                        builder.pathSegment(segment);
                    }
                }

            }

            if (!((queryParamName == null) || (("").equals(queryParamName)))) {

                String[] queryParamNameArr = queryParamName.split(",");
                String[] queryParamValueArr = queryParamValue.split(",");
                for (int i = 0; i < queryParamNameArr.length; i++) {
                    builder.queryParam(queryParamNameArr[i], queryParamValueArr[i]);
                }

            }
            uriComponents = builder.build(false).encode();

            try {
                logger.info("RestApiClient::getApi()::entry uri : {}",apiHostIpPort);
                result = (T) restTemplate
                        .exchange(uriComponents.toUri(), HttpMethod.GET, setRequestHeader(null, null), responseType)
                        .getBody();
            } catch (Exception e) {
                throw new Exception(e);
            }

        }
        return result;
    }
    /**
     * Gets the Object.
     *
     * @param <T>             the generic type
     * @param url         the url
     * @param responseType    the response type
     * @return the api
     * @throws Exception
     */
    @SuppressWarnings("unchecked")
    public <T> T getForObject(String url,
                        Class<?> responseType) throws Exception {

            T result = null;
            try {
                logger.info("RestApiClient::getApi()::entry uri : {}",url);
                result = (T) restTemplate
                        .getForObject(url, responseType);
            } catch (Exception e) {
                throw new Exception(e);
            }
        return result;
    }


    /**
     * Sets the request header.
     *
     * @param requestType the request type
     * @param mediaType   the media type
     * @return the http entity
     * @throws IOException Signals that an I/O exception has occurred.
     */
    @SuppressWarnings("unchecked")
    private HttpEntity<Object> setRequestHeader(Object requestType, MediaType mediaType) throws IOException {
        MultiValueMap<String, String> headers = new LinkedMultiValueMap<>();
        headers.add("Cookie", getToken());
        String contentType="Content-Type";
        if (mediaType != null) {
            headers.add(contentType, mediaType.toString());
        }
        if (requestType != null) {
            try {
                HttpEntity<Object> httpEntity = (HttpEntity<Object>) requestType;
                HttpHeaders httpHeader = httpEntity.getHeaders();
                Iterator<String> iterator = httpHeader.keySet().iterator();
                while (iterator.hasNext()) {
                    String key = iterator.next();
                    List<String> header=httpHeader.get(key);
                    if ( !(headers.containsKey(contentType) && key.equalsIgnoreCase(contentType)) && null!=header && !header.isEmpty())
                        headers.add(key,header.get(0));
                }
                return new HttpEntity<>(httpEntity.getBody(), headers);
            } catch (ClassCastException e) {
                return new HttpEntity<>(requestType, headers);
            }
        } else
            return new HttpEntity<>(headers);
    }


    /**
     * Gets the token.
     *
     * @return the token
     * @throws IOException Signals that an I/O exception has occurred.
     */
    public String getToken() throws IOException {
        String token = System.getProperty("token");
        boolean isValid = false;

        if (StringUtils.isNotEmpty(token)) {

            isValid = TokenHandlerUtil.isValidBearerToken(token,
                    environment.getProperty("token.request.issuerUrl"),
                    environment.getProperty("token.request.clientId"));


        }
        if (!isValid) {
            TokenRequestDTO<SecretKeyRequest> tokenRequestDTO = new TokenRequestDTO<SecretKeyRequest>();
            tokenRequestDTO.setId(environment.getProperty("token.request.id"));
            tokenRequestDTO.setMetadata(new Metadata());

            tokenRequestDTO.setRequesttime(DateUtils.getUTCCurrentDateTimeString());
            // tokenRequestDTO.setRequest(setPasswordRequestDTO());
            tokenRequestDTO.setRequest(setSecretKeyRequestDTO());
            tokenRequestDTO.setVersion(environment.getProperty("token.request.version"));

            Gson gson = new Gson();
            HttpClient httpClient = HttpClientBuilder.create().build();
            HttpPost post = new HttpPost(environment.getProperty("KEYBASEDTOKENAPI"));
            try {
                StringEntity postingString = new StringEntity(gson.toJson(tokenRequestDTO));
                post.setEntity(postingString);
                post.setHeader("Content-type", "application/json");
                HttpResponse response = httpClient.execute(post);
                org.apache.http.HttpEntity entity = response.getEntity();
                String responseBody = EntityUtils.toString(entity, "UTF-8");
                Header[] cookie = response.getHeaders("Set-Cookie");
                if (cookie.length == 0)
                    throw new IOException("cookie is empty. Could not generate new token.");
                token = response.getHeaders("Set-Cookie")[0].getValue();
                System.setProperty("token", token.substring(14, token.indexOf(';')));
                return token.substring(0, token.indexOf(';'));
            } catch (IOException e) {
                throw e;
            }
        }
        return AUTHORIZATION + token;
    }

    private SecretKeyRequest setSecretKeyRequestDTO() {
        SecretKeyRequest request = new SecretKeyRequest();
        request.setAppId(environment.getProperty("token.request.appid"));
        request.setClientId(environment.getProperty("token.request.clientId"));
        request.setSecretKey(environment.getProperty("token.request.secretKey"));
        return request;
    }
}
