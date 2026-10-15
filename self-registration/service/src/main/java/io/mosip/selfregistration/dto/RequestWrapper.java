package io.mosip.selfregistration.dto;

import lombok.Data;

@Data
public class RequestWrapper<T>
{

    private String requestTime;

    private T request;
}
