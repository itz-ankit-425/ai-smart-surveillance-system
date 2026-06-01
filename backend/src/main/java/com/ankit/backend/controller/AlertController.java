package com.ankit.backend.controller;

import com.ankit.backend.model.Alert;
import com.ankit.backend.service.AlertService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@RestController
@CrossOrigin("*")
public class AlertController {

    @Autowired
    private AlertService alertService;

    @PostMapping("/alerts")
    public Alert createAlert(@RequestBody Map<String, Object> data) {

        Alert alert = new Alert();

        alert.setEvent(data.get("event").toString());

        if (data.containsKey("image")) {
            alert.setImage(data.get("image").toString());
        }

        alert.setTimestamp(LocalDateTime.now().toString());

        alert.setThreatLevel("MEDIUM");
        return alertService.saveAlert(alert);
    }

    @GetMapping("/alerts")
    public List<Alert> getAlerts() {
        return alertService.getAllAlerts();
    }
}