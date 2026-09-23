package com.jiheng.controller.profile;

import com.jiheng.dto.ApiResponse;
import com.jiheng.dto.profile.UserProfileDto;
import com.jiheng.service.profile.UserService;
import com.jiheng.util.TraceContext;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 用户资料控制器
 *
 * @author jiheng
 */
@RestController
@RequestMapping("/api/v1/profile")
public class UserController {

    private final UserService userService;
    private final TraceContext traceContext;

    public UserController(UserService userService, TraceContext traceContext) {
        this.userService = userService;
        this.traceContext = traceContext;
    }

    @GetMapping
    public ApiResponse<UserProfileDto> getProfile() {
        return ApiResponse.ok(userService.getProfile(traceContext.getUserId()));
    }

    @PutMapping
    public ApiResponse<Void> updateProfile(@RequestBody Map<String, String> body) {
        userService.updateProfile(traceContext.getUserId(), body.get("displayName"), body.get("avatar"));
        return ApiResponse.ok(null);
    }
}