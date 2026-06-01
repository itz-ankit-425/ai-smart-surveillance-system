package com.ankit.backend.model;

import jakarta.persistence.*;
import lombok.Data;

@Entity
@Data
public class Alert {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String event;

    private String image;

    private String timestamp;

    private String threatLevel;
}