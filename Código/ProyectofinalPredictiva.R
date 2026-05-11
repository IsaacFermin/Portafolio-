view(opioids_total)

#cargar paquetes necesarios
packs <- c("dplyr","ggplot2","tidyr","broom","lmtest","sandwich","car",
           "scales","ggpubr","PerformanceAnalytics","readr")
invisible(lapply(packs, function(p) if(!require(p, character.only=TRUE)) install.packages(p)))
invisible(lapply(packs, library, character.only=TRUE))

#revisar las columnas rapidamente. 
names(opioids_total)
summary(opioids_total$Year)


#Preparando el dataset para el analisis.
#Ojo: ya la data esta limpia y no contiene outliers

#cambiar a numeric la fecha 
opioids_total$Year <- as.numeric(opioids_total$Year)

data <- opioids_total %>%
  arrange(Year) %>%
  mutate(
    NonSynthetic = Number.Opioid.Any - Number.Opioid.Synthetic, # total sin opioides sintéticos
    Year_c = Year - min(Year)                                   # año centrado (mejor numéricamente)
  ) %>%
  select(Year, Year_c,
         Number.Opioid.Any, Number.Opioid.Synthetic,
         Number.Opioid.Heroin, Number.Opioid.Prescription, NonSynthetic)

# Crear Objetos para el análisis principal
y  <- data$Number.Opioid.Any
x  <- data$Number.Opioid.Synthetic
heroin <- data$Number.Opioid.Heroin
rx     <- data$Number.Opioid.Prescription

#Grafico de serie temporal 1; total vs sintéticos

g_series <- data %>%
  select(Year, Total = Number.Opioid.Any, Sinteticos = Number.Opioid.Synthetic) %>%
  pivot_longer(-Year, names_to = "Serie", values_to = "Muertes") %>%
  ggplot(aes(Year, Muertes, group = Serie)) +
  geom_line(linewidth = 1.1) +
  geom_point(size = 2) +
  scale_y_continuous(labels = comma) +
  labs(title = "Muertes por opioides en EE. UU. (1999–2019)",
       subtitle = "Comparación: total vs opioides sintéticos",
       x = "Año", y = "Número de muertes", color = NULL) +
  theme_minimal(base_size = 12)
g_series
ggsave("grafico_serie_total_vs_sinteticos.png", g_series, width = 8, height = 4.5, dpi = 300)


#Grafico sintéticos vs total
g_scatter <- ggplot(data, aes(Number.Opioid.Synthetic, Number.Opioid.Any)) +
  geom_point(size = 2.5, alpha = .9) +
  geom_smooth(method = "lm", se = TRUE) +
  scale_x_continuous(labels = comma) + scale_y_continuous(labels = comma) +
  labs(title = "Relación entre muertes por opioides sintéticos y total por opioides",
       x = "Muertes por opioides sintéticos",
       y = "Muertes totales por opioides") +
  theme_minimal(base_size = 12)
g_scatter
ggsave("grafico_dispersion_sinteticos_vs_total.png", g_scatter, width = 7, height = 5, dpi = 300)

#correlaciones 
corr_df <- data %>%
  select(Total = Number.Opioid.Any,
         Sinteticos = Number.Opioid.Synthetic,
         Heroina = Number.Opioid.Heroin,
         Recetados = Number.Opioid.Prescription,
         Año = Year)

# Matriz de correlaciones 
corr_mat <- round(cor(corr_df, use = "complete.obs"), 3)
corr_mat
write_csv(as.data.frame(corr_mat), "cuadro_correlaciones.csv")



#Regresion lineal. 
# 4.1 Modelo base: Total ~ Sintéticos + tendencia
m1 <- lm(Number.Opioid.Any ~ Number.Opioid.Synthetic + Year_c, data = data)

# 4.2 Modelo con controles: heroína y recetados
m2 <- lm(Number.Opioid.Any ~ Number.Opioid.Synthetic + Number.Opioid.Heroin +
           Number.Opioid.Prescription + Year_c, data = data)

# 4.3 Dependiente alternativa (no sintéticos) para evitar parte–todo
m3 <- lm(NonSynthetic ~ Number.Opioid.Synthetic + Number.Opioid.Heroin +
           Number.Opioid.Prescription + Year_c, data = data)

# Errores estándar robustos HAC (Newey–West) para cada modelo
se_hac_m1 <- sqrt(diag(sandwich::NeweyWest(m1, prewhite = FALSE)))
se_hac_m2 <- sqrt(diag(sandwich::NeweyWest(m2, prewhite = FALSE)))
se_hac_m3 <- sqrt(diag(sandwich::NeweyWest(m3, prewhite = FALSE)))

# Tablas ordenadas (coef, EE robusta, p-valor)
tab_m1 <- broom::tidy(m1) %>% mutate(se_robusta = se_hac_m1, 
                                     t_robusto = estimate/se_robusta,
                                     p_robusto = 2*pt(abs(t_robusto), df = m1$df.residual, lower.tail = FALSE))
tab_m2 <- broom::tidy(m2) %>% mutate(se_robusta = se_hac_m2,
                                     t_robusto = estimate/se_robusta,
                                     p_robusto = 2*pt(abs(t_robusto), df = m2$df.residual, lower.tail = FALSE))
tab_m3 <- broom::tidy(m3) %>% mutate(se_robusta = se_hac_m3,
                                     t_robusto = estimate/se_robusta,
                                     p_robusto = 2*pt(abs(t_robusto), df = m3$df.residual, lower.tail = FALSE))

tab_m1; tab_m2; tab_m3
write_csv(tab_m1, "tabla_m1_base.csv")
write_csv(tab_m2, "tabla_m2_controles.csv")
write_csv(tab_m3, "tabla_m3_nosinteticos.csv")



#Pruebas de validacion


# 5.1 Autocorrelación (Durbin–Watson) y heterocedasticidad (Breusch–Pagan)
lmtest::dwtest(m2)
lmtest::bptest(m2)

# 5.2 Colinealidad (VIF)
car::vif(m2)

# 5.3 Gráficos de residuos del modelo principal (m2)
resid_plot1 <- ggplot(m2, aes(.fitted, .resid)) +
  geom_point() + geom_hline(yintercept = 0, linetype = 2) +
  labs(x = "Valores ajustados", y = "Residuos", title = "Residuos vs Ajustados (m2)") +
  theme_minimal()
resid_plot2 <- ggpubr::ggqqplot(residuals(m2)) + ggtitle("QQ-plot de residuos (m2)")

resid_plot1; resid_plot2
ggsave("residuos_vs_ajustados_m2.png", resid_plot1, width = 7, height = 4.5, dpi = 300)
ggsave("qqplot_residuos_m2.png", resid_plot2, width = 6, height = 5, dpi = 300)



