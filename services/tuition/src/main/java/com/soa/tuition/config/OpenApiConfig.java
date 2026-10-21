package com.soa.tuition.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("Quản lý Sinh viên & Dịch vụ OTP (Nguyên)")
                        .version("1.0.0")
                        .description("Microservice phụ trách Quản lý Sinh viên, Học phí và Xác thực mã OTP thanh toán (Spring Boot 3 - Java 17)."));
    }
}
