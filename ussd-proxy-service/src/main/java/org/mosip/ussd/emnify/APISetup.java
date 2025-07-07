package org.mosip.ussd.emnify;

import java.io.IOException;
import java.util.HashSet;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import okhttp3.Interceptor;
import okhttp3.OkHttpClient;
import okhttp3.Request;
//import retrofit2.GsonConverterFactory;
import retrofit2.Retrofit;
import retrofit2.adapter.java8.Java8CallAdapterFactory;
import retrofit2.converter.gson.GsonConverterFactory;
import okhttp3.logging.HttpLoggingInterceptor;


public class APISetup {
	   private static Retrofit retrofit = null;
	    private static HashSet<String> cookies  = new HashSet<>();
		private static final Logger logger = LoggerFactory.getLogger(APISetup.class);

		private static String token;
		private String emnifyUrlBase;
		public APISetup(String urlBase) {
			emnifyUrlBase = urlBase;
		}
		public static void setToken(String tkn) {
			token = tkn;
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
	            builder.addHeader("Authorization", "Bearer " + token );
	            builder.addHeader("Accept","*/*");
	            builder.addHeader("Connection","keep-alive");
	           // builder.addHeader("Accept-Encoding","gzip, deflate, br");
	           // builder.addHeader("User-Agent","PostmanRuntime/7.28.4");
	            //builder.addHeader("Host","sandbox.mosip.net");

	            return chain.proceed(builder.build());
	        }
	    }
	    public  Retrofit getClient() {

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
	                .setLenient()
	                .enableComplexMapKeySerialization()
	                
	                .create();

	        logger.info(emnifyUrlBase);
	        retrofit = new Retrofit.Builder()
	         //       .baseUrl("https://sandbox.mosip.net")
	                .baseUrl(emnifyUrlBase)
	      //          .addConverterFactory(ScalarsConverterFactory.create())
	                .addCallAdapterFactory(Java8CallAdapterFactory.create())
	                .addConverterFactory(GsonConverterFactory.create( gson))
	                
	                //  .addCallAdapterFactory(RxJava2CallAdapterFactory.create())
	                .client(client)
	                .build();
	        return retrofit;
	    }
}
