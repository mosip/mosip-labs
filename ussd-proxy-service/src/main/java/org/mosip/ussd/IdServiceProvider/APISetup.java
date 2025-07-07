package org.mosip.ussd.IdServiceProvider;


import com.google.gson.Gson;
import com.google.gson.GsonBuilder;


import java.io.IOException;
import java.util.HashSet;

import okhttp3.Interceptor;
import okhttp3.Request;

import retrofit2.adapter.java8.Java8CallAdapterFactory;
import retrofit2.converter.gson.GsonConverterFactory;
import retrofit2.Retrofit;
import okhttp3.logging.HttpLoggingInterceptor;
import okhttp3.OkHttpClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class APISetup {

    private static final Logger logger = LoggerFactory.getLogger(APISetup.class);
    private static Retrofit retrofit = null;
    private static HashSet<String> cookies  = new HashSet<>();
    private static String baseUrl;
   

    public APISetup(String tbaseUrl){
        baseUrl = tbaseUrl;
    }
    static class ReceivedCookiesInterceptor implements Interceptor {
        @Override
        public okhttp3.Response intercept(Chain chain) throws IOException {
            okhttp3.Response originalResponse = chain.proceed(chain.request());

            if (!originalResponse.headers("Set-Cookie").isEmpty()) {


                for (String header : originalResponse.headers("Set-Cookie")) {
                    logger.info("OkHttp", "Got Cookie: " + header);
                    cookies.add(header);
                }
            }
            return originalResponse;
        }
    }
    static class AddCookiesInterceptor implements Interceptor {

        @Override
        public okhttp3.Response intercept(Chain chain) throws IOException {
            Request.Builder builder = chain.request().newBuilder();

            for (String cookie : cookies) {
                builder.addHeader("Cookie", cookie);
                logger.info("OkHttp", "Adding Header: " + cookie);//This is done so I know which headers are being added; this interceptor is used after the normal logging of OkHttp
            }
            builder.addHeader("Accept","*/*");
            builder.addHeader("Connection","keep-alive");
            builder.addHeader("Accept-Encoding","gzip, deflate, br");
           // builder.addHeader("User-Agent","PostmanRuntime/7.28.4");
            //builder.addHeader("Host","sandbox.mosip.net");

            return chain.proceed(builder.build());
        }
    }
    public static Retrofit getClient() {
        return getClient(baseUrl);
    }
    public static Retrofit getClient(String baseUrl) {

        HttpLoggingInterceptor interceptor = new HttpLoggingInterceptor();
        interceptor.setLevel(HttpLoggingInterceptor.Level.BODY);
        OkHttpClient client = new OkHttpClient.Builder()
                .addInterceptor (new AddCookiesInterceptor ())
                .addInterceptor (new ReceivedCookiesInterceptor ())
                .addInterceptor(interceptor)
                .build();


        Gson gson = new GsonBuilder()
                .setLenient()
                .serializeNulls()
                .setPrettyPrinting()
                .create();

        retrofit = new Retrofit.Builder()
         
                .baseUrl(baseUrl)
                .addConverterFactory(GsonConverterFactory.create(gson))
                .addCallAdapterFactory(Java8CallAdapterFactory.create())
              
                .client(client)
                .build();
        return retrofit;
    }

   

}
