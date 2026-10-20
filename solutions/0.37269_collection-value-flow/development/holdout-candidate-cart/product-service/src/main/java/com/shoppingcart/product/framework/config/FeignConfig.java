package com.shoppingcart.product.framework.config;

import feign.Client;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import java.security.cert.X509Certificate;

@Configuration
public class FeignConfig {

    @Bean
    public Client feignClient() {
        try {
            TrustManager[] trustAllCerts = new TrustManager[]{
                new X509TrustManager() {
                    public X509Certificate[] getAcceptedIssuers() { return new X509Certificate[0]; }
                    public void checkClientTrusted(X509Certificate[] certs, String authType) {}
                    public void checkServerTrusted(X509Certificate[] certs, String authType) {}
                }
            };

            SSLContext context = SSLContext.getInstance("TLS");
            context.init(null, trustAllCerts, new java.security.SecureRandom());

            return new Client.Default(context.getSocketFactory(),
                    (hostname, session) -> true);

        } catch (Exception e) {
            throw new RuntimeException("Error configurando Feign SSL", e);
        }
    }
}
