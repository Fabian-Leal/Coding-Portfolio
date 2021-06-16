##########################################################
# Modelo de atrasos en minutos univariado por RUT
##########################################################

# Lee el archivo
ruta_1 <- "C://Users//Fabian//Desktop//SCM//"
archivo_1 <- "BD_CONSOLIDADA.csv"
datos <- read.csv(paste(ruta_1,archivo_1, sep=""), sep=";")

# Lee el archivo
ruta_2 <- "C://Users//Fabian//Desktop//SCM//"
archivo_2 <- "DI_Feriados.csv"
feriados <- read.csv(paste(ruta_2,archivo_2, sep=""), sep=";")

# Ordena cronologicamente por persona
datos$DATE_RPT <- strptime(datos$DATE_RPT, format='%Y-%m-%d %H:%M:%S')
datos <- datos[order(datos$RUT,datos$DATE_RPT),]

datos$HoraEntrada <- paste(substr(datos$DATE_RPT,1,10), substr(datos$turno,1,5))
datos$HoraSalida <- paste(substr(datos$DATE_RPT,1,10), substr(datos$turno,7,11))
datos$MarcaEntrada <- paste(substr(datos$DATE_RPT,1,10), substr(datos$MARCAS,1,5))
datos$MarcaSalida <- paste(substr(datos$DATE_RPT,1,10), substr(datos$MARCAS,9,13))

datos$HoraEntrada <- ifelse(datos$turno == 'LIBRE',NA,datos$HoraEntrada)
datos$HoraSalida <- ifelse(datos$turno == 'LIBRE',NA,datos$HoraSalida)
datos$MarcaEntrada <- ifelse(datos$MARCAS == 'xx:xx | xx:xx', NA,datos$MarcaEntrada)
datos$MarcaEntrada <- ifelse(datos$MARCAS == '', NA,datos$MarcaEntrada)
datos$MarcaSalida <- ifelse(datos$MARCAS == 'xx:xx | xx:xx', NA,datos$MarcaSalida)
datos$MarcaSalida <- ifelse(datos$MARCAS == '', NA,datos$MarcaSalida)

# Transforma formato date con hora "2006-01-08 10:07:52"
datos$HoraEntrada <- strptime(datos$HoraEntrada, format = "%Y-%m-%d %H:%M")
datos$HoraSalida <- strptime(datos$HoraSalida, format = "%Y-%m-%d %H:%M")
datos$MarcaEntrada <- strptime(datos$MarcaEntrada, format = "%Y-%m-%d %H:%M")
datos$MarcaSalida <- strptime(datos$MarcaSalida, format = "%Y-%m-%d %H:%M")

# Calculo del total de horas laborales oficiales
datos$HorasLaboralesOficial <- round(abs(as.numeric(difftime(datos$HoraSalida,datos$HoraEntrada, tz="EST", units = "hours"))),1)

# Calculo del total de horas laborales trabajadas
datos$HorasLaboralesTrabajadas <- round(abs(as.numeric(difftime(datos$MarcaSalida,datos$MarcaEntrada, tz="EST", units = "hours"))),1)

# Calculo del diferencia entre la llegada y su hora oficial de entrada
datos$MinutosAtrasos <- as.numeric(round((datos$MarcaEntrada - datos$HoraEntrada)/60,1))

# Marca si la persona registro atraso o No
datos$Atrasado <- ifelse(datos$MinutosAtrasos > 0, "SI","NO")

# Marca si la persona si presenta ausentismo
datos$Ausentismo <- ifelse(datos$MOTIVO_AUSENCIA == "ACC.TRABAJO" | 
                             datos$MOTIVO_AUSENCIA == "Aniversario Abastible" | 
                             datos$MOTIVO_AUSENCIA == "Atraso Justificado" | 
                             datos$MOTIVO_AUSENCIA == "Capacitación" | 
                             datos$MOTIVO_AUSENCIA == "CAPACITACION SC" | 
                             datos$MOTIVO_AUSENCIA == "COMISION DE SERVICIO" | 
                             datos$MOTIVO_AUSENCIA == "COMPENSACION DIA DOMINGO" | 
                             datos$MOTIVO_AUSENCIA == "COMPENSACION DIA FERIADO" | 
                             datos$MOTIVO_AUSENCIA == "COMPENSACION DIA NORMAL" | 
                             datos$MOTIVO_AUSENCIA == "CONCILIACION FAMILIAR" | 
                             datos$MOTIVO_AUSENCIA == "DIA ADMINISTRATIVO" | 
                             datos$MOTIVO_AUSENCIA == "DIA FESTIVO" | 
                             datos$MOTIVO_AUSENCIA == "Examen Ocupacional" | 
                             datos$MOTIVO_AUSENCIA == "FALTA" | 
                             datos$MOTIVO_AUSENCIA == "Fiesta Navidad" | 
                             datos$MOTIVO_AUSENCIA == "LICENCIA" | 
                             datos$MOTIVO_AUSENCIA == "MATERNAL" | 
                             datos$MOTIVO_AUSENCIA == "Olimpiadas Abastible" | 
                             datos$MOTIVO_AUSENCIA == "PASEO DE FIN DE AÑO" | 
                             datos$MOTIVO_AUSENCIA == "PERMISO" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Alimentacion Hijo" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Autorizado" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Cumpleaños" | 
                             datos$MOTIVO_AUSENCIA == "PERMISO FALLECIMIENTO" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Fiestas Patrias" | 
                             datos$MOTIVO_AUSENCIA == "PERMISO MATRIMONIO" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Medico" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Medio Dia Administrativo" | 
                             datos$MOTIVO_AUSENCIA == "PERMISO NACIMIENTO" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Navidad y Año Nuevo" | 
                             datos$MOTIVO_AUSENCIA == "PERMISO RECUPERADO" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Sindical" | 
                             datos$MOTIVO_AUSENCIA == "Salida Temprana Justificada" | 
                             datos$MOTIVO_AUSENCIA == "VACACIONES",
                             "SI","NO")
                             
# sub data para modelo forecast de los atrasos en minutos
sub.data.atrasos <- datos[!is.na(datos$MinutosAtrasos),]
length(unique(sub.data.atrasos$RUT))

# Contruyendo minutos atrasados por persona en el tiempo
if('reshape2' %in% rownames(installed.packages()) == FALSE) {install.packages('reshape2')}
library(reshape2)
input.atrasos <- sub.data.atrasos[,c(1,46,50)]
input.atrasos$MarcaEntrada <- as.Date(input.atrasos$MarcaEntrada)
datos.transp <- dcast(input.atrasos, MarcaEntrada ~ RUT, sum)

# asigna a los ceros un NA
system.time(
  for(i in 2:ncol(datos.transp)){
    datos.transp[datos.transp[,i]==0,i] <- NA
  }
)

# Formato para los feriados
if('dplyr' %in% rownames(installed.packages()) == FALSE) {install.packages('dplyr')}
library(dplyr)
feriados$festivos <- as.character(feriados$festivos)
feriados$ds <- as.Date(feriados$ds, format='%d-%m-%Y')
feriados$lower_window <- as.numeric(feriados$lower_window)
feriados$upper_window <- as.numeric(feriados$upper_window)
holidays_festivos <- data_frame(holiday = feriados$festivos, ds =feriados$ds, lower_window = 0, upper_window = 1)
holidays <- bind_rows(holidays_festivos)

# Funcion predictor de atrasos futuros (Minutos)
if('prophet' %in% rownames(installed.packages()) == FALSE) {install.packages('prophet')}
if('stringr' %in% rownames(installed.packages()) == FALSE) {install.packages('stringr')}
if('ggplot2' %in% rownames(installed.packages()) == FALSE) {install.packages('ggplot2')}
library(prophet)
library(stringr)
library(ggplot2)

# limpiar los ceros (sin observaciones para una persona)
if('imputeTS' %in% rownames(installed.packages()) == FALSE) {install.packages('imputeTS')}
library(imputeTS)

# Eliminar RUT que tienen menos de 3 registros de entradas historicas
num_na_rut <- NULL

system.time(
  for(j in 2:ncol(datos.transp)){
    num_na_rut <- rbind(num_na_rut, sum(is.na(datos.transp[,j])))
  }
)

num_maximo_na_marcas_por_rut <- nrow(datos.transp)-7

secuencia <- seq(2,ncol(datos.transp))
Rut_validos <- data.frame(secuencia,num_na_rut)

Rut_validos <- Rut_validos[Rut_validos$num_na_rut > num_maximo_na_marcas_por_rut,]

datos.transp <- datos.transp[,-c(Rut_validos$secuencia)]

# Iteracion de prediccion univariada por RUT: Atrasos en minutos
salida.atrasos<-NULL

system.time(
  for(i in 2:ncol(datos.transp)){
  modelo <- prophet(data.frame(ds=datos.transp[,1],
                    y=na.kalman(datos.transp[,i], model = "auto.arima")),
                    yearly.seasonality = TRUE,
                    weekly.seasonality = TRUE,
                    daily.seasonality = TRUE,
                    holidays = holidays,
                    algorithm='Newton')
  
  futuro <- make_future_dataframe(modelo, periods = 90, freq = "day", include_history = TRUE)
  prediccion <- predict(modelo, futuro)[c('ds','yhat','yhat_lower','yhat_upper')]
  graf <- plot(modelo, prediccion, ylab="Atrasos (minutos)", xlab="Periodo")
  titulo <- ggtitle(paste('Rut', names(datos.transp[i]),', Error de Prediccion es',
                         sprintf("%1.2f%%", 100*(modelo$params$sigma_obs))))
  print(graf+titulo)
  RUT_Trabajador <- as.matrix(rep(names(datos.transp[i]),dim(prediccion)[1]))
  colnames(RUT_Trabajador) <- "RUT_Trabajador"
  output <- cbind(RUT_Trabajador,graf$data)
  salida.atrasos <- rbind(salida.atrasos, output)
})

write.csv2(salida.atrasos,'Predictor_atrasos_minutos_90_dias.csv')

save.image("~/Predictor_atrasos_minutos_90_dias.RData")

##########################################################
# Modelo del N° ausentismo multivariado por RUT
##########################################################

# Lee el archivo
ruta_1 <- "C://Users//bebellor//Desktop//Proyecto Roberto Alfaro SCM//"
archivo_1 <- "BD_CONSOLIDADA.csv"
datos <- read.csv(paste(ruta_1,archivo_1, sep=""), sep=";")

# Lee el archivo
ruta_2 <- "C://Users//bebellor//Desktop//Proyecto Roberto Alfaro SCM//"
archivo_2 <- "DI_Feriados.csv"
feriados <- read.csv(paste(ruta_2,archivo_2, sep=""), sep=";")

# Ordena cronologicamente por persona
datos$DATE_RPT <- strptime(datos$DATE_RPT, format='%Y-%m-%d %H:%M:%S')
datos <- datos[order(datos$RUT,datos$DATE_RPT),]

datos$HoraEntrada <- paste(substr(datos$DATE_RPT,1,10), substr(datos$turno,1,5))
datos$HoraSalida <- paste(substr(datos$DATE_RPT,1,10), substr(datos$turno,7,11))
datos$MarcaEntrada <- paste(substr(datos$DATE_RPT,1,10), substr(datos$MARCAS,1,5))
datos$MarcaSalida <- paste(substr(datos$DATE_RPT,1,10), substr(datos$MARCAS,9,13))

datos$HoraEntrada <- ifelse(datos$turno == 'LIBRE',NA,datos$HoraEntrada)
datos$HoraSalida <- ifelse(datos$turno == 'LIBRE',NA,datos$HoraSalida)
datos$MarcaEntrada <- ifelse(datos$MARCAS == 'xx:xx | xx:xx', NA,datos$MarcaEntrada)
datos$MarcaEntrada <- ifelse(datos$MARCAS == '', NA,datos$MarcaEntrada)
datos$MarcaSalida <- ifelse(datos$MARCAS == 'xx:xx | xx:xx', NA,datos$MarcaSalida)
datos$MarcaSalida <- ifelse(datos$MARCAS == '', NA,datos$MarcaSalida)

# Transforma formato date con hora "2006-01-08 10:07:52"
datos$HoraEntrada <- strptime(datos$HoraEntrada, format = "%Y-%m-%d %H:%M")
datos$HoraSalida <- strptime(datos$HoraSalida, format = "%Y-%m-%d %H:%M")
datos$MarcaEntrada <- strptime(datos$MarcaEntrada, format = "%Y-%m-%d %H:%M")
datos$MarcaSalida <- strptime(datos$MarcaSalida, format = "%Y-%m-%d %H:%M")

# Calculo del total de horas laborales oficiales
datos$HorasLaboralesOficial <- round(abs(as.numeric(difftime(datos$HoraSalida,datos$HoraEntrada, tz="EST", units = "hours"))),1)

# Calculo del total de horas laborales trabajadas
datos$HorasLaboralesTrabajadas <- round(abs(as.numeric(difftime(datos$MarcaSalida,datos$MarcaEntrada, tz="EST", units = "hours"))),1)

# Calculo del diferencia entre la llegada y su hora oficial de entrada
datos$MinutosAtrasos <- as.numeric(round((datos$MarcaEntrada - datos$HoraEntrada)/60,1))

# Marca si la persona registro atraso o No
datos$Atrasado <- ifelse(datos$MinutosAtrasos > 0, "SI","NO")

# Marca si la persona si presenta ausentismo
datos$Ausentismo <- ifelse(datos$MOTIVO_AUSENCIA == "ACC.TRABAJO" | 
                             datos$MOTIVO_AUSENCIA == "Aniversario Abastible" | 
                             datos$MOTIVO_AUSENCIA == "Atraso Justificado" | 
                             datos$MOTIVO_AUSENCIA == "Capacitación" | 
                             datos$MOTIVO_AUSENCIA == "CAPACITACION SC" | 
                             datos$MOTIVO_AUSENCIA == "COMISION DE SERVICIO" | 
                             datos$MOTIVO_AUSENCIA == "COMPENSACION DIA DOMINGO" | 
                             datos$MOTIVO_AUSENCIA == "COMPENSACION DIA FERIADO" | 
                             datos$MOTIVO_AUSENCIA == "COMPENSACION DIA NORMAL" | 
                             datos$MOTIVO_AUSENCIA == "CONCILIACION FAMILIAR" | 
                             datos$MOTIVO_AUSENCIA == "DIA ADMINISTRATIVO" | 
                             datos$MOTIVO_AUSENCIA == "DIA FESTIVO" | 
                             datos$MOTIVO_AUSENCIA == "Examen Ocupacional" | 
                             datos$MOTIVO_AUSENCIA == "FALTA" | 
                             datos$MOTIVO_AUSENCIA == "Fiesta Navidad" | 
                             datos$MOTIVO_AUSENCIA == "LICENCIA" | 
                             datos$MOTIVO_AUSENCIA == "MATERNAL" | 
                             datos$MOTIVO_AUSENCIA == "Olimpiadas Abastible" | 
                             datos$MOTIVO_AUSENCIA == "PASEO DE FIN DE AÑO" | 
                             datos$MOTIVO_AUSENCIA == "PERMISO" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Alimentacion Hijo" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Autorizado" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Cumpleaños" | 
                             datos$MOTIVO_AUSENCIA == "PERMISO FALLECIMIENTO" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Fiestas Patrias" | 
                             datos$MOTIVO_AUSENCIA == "PERMISO MATRIMONIO" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Medico" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Medio Dia Administrativo" | 
                             datos$MOTIVO_AUSENCIA == "PERMISO NACIMIENTO" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Navidad y Año Nuevo" | 
                             datos$MOTIVO_AUSENCIA == "PERMISO RECUPERADO" | 
                             datos$MOTIVO_AUSENCIA == "Permiso Sindical" | 
                             datos$MOTIVO_AUSENCIA == "Salida Temprana Justificada" |
                             datos$MOTIVO_AUSENCIA == "VACACIONES",
                           "SI","NO")

if('reshape2' %in% rownames(installed.packages()) == FALSE) {install.packages('reshape2')}
library(reshape2)

datos$Ausentismo <- ifelse(datos$Ausentismo == 'SI',1,0)
datos$Atrasado <- ifelse(datos$Atrasado == 'SI',1,0)

# Filtramos solo los activos
datos <- datos[datos$Estado_Desc == 'Activo',]

# Contar los ausentismos en todo el periodo laboral
datos.ausentismos <- dcast(datos, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(datos.ausentismos)[3] <- "Total_Num_Ausentismos"
datos.ausentismos  <- datos.ausentismos[,c(1,3)]

datos.Num_Ausentismos_1M <- datos[datos$DATE_RPT > (max(datos$DATE_RPT)-(3600*24*30)) & datos$DATE_RPT <= max(datos$DATE_RPT),]
datos.Num_Ausentismos_1M <- dcast(datos.Num_Ausentismos_1M, datos.Num_Ausentismos_1M$RUT ~ datos.Num_Ausentismos_1M$Ausentismo, fun.aggregate = sum)
colnames(datos.Num_Ausentismos_1M)[3] <- "Total_Num_Ausentismos_1M"
colnames(datos.Num_Ausentismos_1M)[1] <- "RUT"
datos.Num_Ausentismos_1M  <- datos.Num_Ausentismos_1M[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, datos.Num_Ausentismos_1M, by.x="RUT", by.y="RUT",all.x=TRUE)

datos.Num_Ausentismos_3M <- datos[datos$DATE_RPT > (max(datos$DATE_RPT)-(3600*24*90)) & datos$DATE_RPT <= max(datos$DATE_RPT),]
datos.Num_Ausentismos_3M <- dcast(datos.Num_Ausentismos_3M, datos.Num_Ausentismos_3M$RUT ~ datos.Num_Ausentismos_3M$Ausentismo, fun.aggregate = sum)
colnames(datos.Num_Ausentismos_3M)[3] <- "Total_Num_Ausentismos_3M"
colnames(datos.Num_Ausentismos_3M)[1] <- "RUT"
datos.Num_Ausentismos_3M  <- datos.Num_Ausentismos_3M[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, datos.Num_Ausentismos_3M, by.x="RUT", by.y="RUT",all.x=TRUE)

datos.Num_Ausentismos_6M <- datos[datos$DATE_RPT > (max(datos$DATE_RPT)-(3600*24*180)) & datos$DATE_RPT <= max(datos$DATE_RPT),]
datos.Num_Ausentismos_6M <- dcast(datos.Num_Ausentismos_6M, datos.Num_Ausentismos_6M$RUT ~ datos.Num_Ausentismos_6M$Ausentismo, fun.aggregate = sum)
colnames(datos.Num_Ausentismos_6M)[3] <- "Total_Num_Ausentismos_6M"
colnames(datos.Num_Ausentismos_6M)[1] <- "RUT"
datos.Num_Ausentismos_6M  <- datos.Num_Ausentismos_6M[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, datos.Num_Ausentismos_6M, by.x="RUT", by.y="RUT",all.x=TRUE)

datos.Num_Ausentismos_9M <- datos[datos$DATE_RPT > (max(datos$DATE_RPT)-(3600*24*270)) & datos$DATE_RPT <= max(datos$DATE_RPT),]
datos.Num_Ausentismos_9M <- dcast(datos.Num_Ausentismos_9M, datos.Num_Ausentismos_9M$RUT ~ datos.Num_Ausentismos_9M$Ausentismo, fun.aggregate = sum)
colnames(datos.Num_Ausentismos_9M)[3] <- "Total_Num_Ausentismos_9M"
colnames(datos.Num_Ausentismos_9M)[1] <- "RUT"
datos.Num_Ausentismos_9M  <- datos.Num_Ausentismos_9M[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, datos.Num_Ausentismos_9M, by.x="RUT", by.y="RUT",all.x=TRUE)

datos.Num_Ausentismos_12M <- datos[datos$DATE_RPT > (max(datos$DATE_RPT)-(3600*24*360)) & datos$DATE_RPT <= max(datos$DATE_RPT),]
datos.Num_Ausentismos_12M <- dcast(datos.Num_Ausentismos_12M, datos.Num_Ausentismos_12M$RUT ~ datos.Num_Ausentismos_12M$Ausentismo, fun.aggregate = sum)
colnames(datos.Num_Ausentismos_12M)[3] <- "Total_Num_Ausentismos_12M"
colnames(datos.Num_Ausentismos_12M)[1] <- "RUT"
datos.Num_Ausentismos_12M  <- datos.Num_Ausentismos_12M[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, datos.Num_Ausentismos_12M, by.x="RUT", by.y="RUT",all.x=TRUE)

# Conteos de atrasos por semana
datos.Num_Ausentismos_1S <- datos[datos$DATE_RPT > (max(datos$DATE_RPT)-(3600*24*7)) & datos$DATE_RPT <= max(datos$DATE_RPT),]
datos.Num_Ausentismos_1S <- dcast(datos.Num_Ausentismos_1S, datos.Num_Ausentismos_1S$RUT ~ datos.Num_Ausentismos_1S$Ausentismo, fun.aggregate = sum)
colnames(datos.Num_Ausentismos_1S)[3] <- "Total_Num_Ausentismos_1S"
colnames(datos.Num_Ausentismos_1S)[1] <- "RUT"
datos.Num_Ausentismos_1S  <- datos.Num_Ausentismos_1S[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, datos.Num_Ausentismos_1S, by.x="RUT", by.y="RUT",all.x=TRUE)

datos.Num_Ausentismos_2S <- datos[datos$DATE_RPT > (max(datos$DATE_RPT)-(3600*24*14)) & datos$DATE_RPT <= max(datos$DATE_RPT),]
datos.Num_Ausentismos_2S <- dcast(datos.Num_Ausentismos_2S, datos.Num_Ausentismos_2S$RUT ~ datos.Num_Ausentismos_2S$Ausentismo, fun.aggregate = sum)
colnames(datos.Num_Ausentismos_2S)[3] <- "Total_Num_Ausentismos_2S"
colnames(datos.Num_Ausentismos_2S)[1] <- "RUT"
datos.Num_Ausentismos_2S  <- datos.Num_Ausentismos_2S[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, datos.Num_Ausentismos_2S, by.x="RUT", by.y="RUT",all.x=TRUE)

datos.Num_Ausentismos_3S <- datos[datos$DATE_RPT > (max(datos$DATE_RPT)-(3600*24*21)) & datos$DATE_RPT <= max(datos$DATE_RPT),]
datos.Num_Ausentismos_3S <- dcast(datos.Num_Ausentismos_3S, datos.Num_Ausentismos_3S$RUT ~ datos.Num_Ausentismos_3S$Ausentismo, fun.aggregate = sum)
colnames(datos.Num_Ausentismos_3S)[3] <- "Total_Num_Ausentismos_3S"
colnames(datos.Num_Ausentismos_3S)[1] <- "RUT"
datos.Num_Ausentismos_3S  <- datos.Num_Ausentismos_3S[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, datos.Num_Ausentismos_3S, by.x="RUT", by.y="RUT",all.x=TRUE)

datos.Num_Ausentismos_4S <- datos[datos$DATE_RPT > (max(datos$DATE_RPT)-(3600*24*30)) & datos$DATE_RPT <= max(datos$DATE_RPT),]
datos.Num_Ausentismos_4S <- dcast(datos.Num_Ausentismos_4S, datos.Num_Ausentismos_4S$RUT ~ datos.Num_Ausentismos_4S$Ausentismo, fun.aggregate = sum)
colnames(datos.Num_Ausentismos_4S)[3] <- "Total_Num_Ausentismos_4S"
colnames(datos.Num_Ausentismos_4S)[1] <- "RUT"
datos.Num_Ausentismos_4S  <- datos.Num_Ausentismos_4S[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, datos.Num_Ausentismos_4S, by.x="RUT", by.y="RUT",all.x=TRUE)

# Contar los atrasos en todo el periodo laboral
subdata.atraso.sin.na <- datos[,-ncol(datos)]
sub.datos.atrasos <- dcast(subdata.atraso.sin.na, RUT ~ Atrasado, fun.aggregate = sum)
colnames(sub.datos.atrasos )[3] <- "Total_Num_Atrasos"
colnames(sub.datos.atrasos )[1] <- "RUT"
datos.atrasos  <- sub.datos.atrasos [,c(1,3)]
# agregamos total de atrassos historico por RUt e imputaos los NA por 0
datos.ausentismos <- merge(datos.ausentismos, datos.atrasos, by.x="RUT", by.y="RUT",all.x=TRUE)

# Contar los ausentismos de Lunes al Domingo por dia
sub.data.lunes <- datos[datos$DIA == 'LUNES',]
sub.data.lunes <- dcast(sub.data.lunes, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.lunes)[3] <- "Total_Num_Ausentismo_Lunes"
colnames(sub.data.lunes)[1] <- "RUT"
sub.data.lunes <- sub.data.lunes[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.lunes, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.martes <- datos[datos$DIA == 'MARTES',]
sub.data.martes <- dcast(sub.data.martes, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.martes)[3] <- "Total_Num_Ausentismo_Martes"
colnames(sub.data.martes)[1] <- "RUT"
sub.data.martes <- sub.data.martes[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.martes, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.miercoles <- datos[datos$DIA == 'MIERCOLES',]
sub.data.miercoles <- dcast(sub.data.miercoles, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.miercoles)[3] <- "Total_Num_Ausentismo_Miercoles"
colnames(sub.data.miercoles)[1] <- "RUT"
sub.data.miercoles <- sub.data.miercoles[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.miercoles, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.jueves <- datos[datos$DIA == 'JUEVES',]
sub.data.jueves <- dcast(sub.data.jueves, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.jueves)[3] <- "Total_Num_Ausentismo_Jueves"
colnames(sub.data.jueves)[1] <- "RUT"
sub.data.jueves <- sub.data.jueves[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.jueves, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.viernes <- datos[datos$DIA == 'VIERNES',]
sub.data.viernes <- dcast(sub.data.viernes, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.viernes)[3] <- "Total_Num_Ausentismo_Viernes"
colnames(sub.data.viernes)[1] <- "RUT"
sub.data.viernes <- sub.data.viernes[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.viernes, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.sabado <- datos[datos$DIA == 'SABADO',]
sub.data.sabado <- dcast(sub.data.sabado, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.sabado)[3] <- "Total_Num_Ausentismo_Sabado"
colnames(sub.data.sabado)[1] <- "RUT"
sub.data.sabado <- sub.data.sabado[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.sabado, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.domingo <- datos[datos$DIA == 'DOMINGO',]
sub.data.domingo <- dcast(sub.data.domingo, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.domingo)[3] <- "Total_Num_Ausentismo_Domingo"
colnames(sub.data.domingo)[1] <- "RUT"
sub.data.domingo <- sub.data.domingo[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.domingo, by.x="RUT", by.y="RUT",all.x=TRUE)

# Construyendo el MES en el dataset datos
datos$MES <- format(datos$DATE_RPT, "%B")
datos$MES <- as.factor(datos$MES)

datos <- datos[,c(1:29,53,30:52)]
# Contar los ausentismos ENERO-DICIEMBRE por MES
sub.data.enero <- datos[datos$MES == 'enero',]
sub.data.enero <- dcast(sub.data.enero, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.enero)[3] <- "Total_Num_Ausentismo_Enero"
colnames(sub.data.enero)[1] <- "RUT"
sub.data.enero <- sub.data.enero[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.enero, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.febrero <- datos[datos$MES == 'febrero',]
sub.data.febrero <- dcast(sub.data.febrero, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.febrero)[3] <- "Total_Num_Ausentismo_Febrero"
colnames(sub.data.febrero)[1] <- "RUT"
sub.data.febrero <- sub.data.febrero[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.febrero, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.marzo <- datos[datos$MES == 'marzo',]
sub.data.marzo <- dcast(sub.data.marzo, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.marzo)[3] <- "Total_Num_Ausentismo_Marzo"
colnames(sub.data.marzo)[1] <- "RUT"
sub.data.marzo <- sub.data.marzo[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.marzo, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.abril <- datos[datos$MES == 'abril',]
sub.data.abril <- dcast(sub.data.abril, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.abril)[3] <- "Total_Num_Ausentismo_Abril"
colnames(sub.data.abril)[1] <- "RUT"
sub.data.abril <- sub.data.abril[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.abril, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.mayo <- datos[datos$MES == 'mayo',]
sub.data.mayo <- dcast(sub.data.mayo, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.mayo)[3] <- "Total_Num_Ausentismo_Mayo"
colnames(sub.data.mayo)[1] <- "RUT"
sub.data.mayo <- sub.data.mayo[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.mayo, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.junio <- datos[datos$MES == 'junio',]
sub.data.junio <- dcast(sub.data.junio, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.junio)[3] <- "Total_Num_Ausentismo_Junio"
colnames(sub.data.junio)[1] <- "RUT"
sub.data.junio <- sub.data.junio[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.junio, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.julio <- datos[datos$MES == 'julio',]
sub.data.julio <- dcast(sub.data.julio, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.julio)[3] <- "Total_Num_Ausentismo_Julio"
colnames(sub.data.julio)[1] <- "RUT"
sub.data.julio <- sub.data.julio[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.julio, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.agosto <- datos[datos$MES == 'agosto',]
sub.data.agosto <- dcast(sub.data.agosto, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.agosto)[3] <- "Total_Num_Ausentismo_Agosto"
colnames(sub.data.agosto)[1] <- "RUT"
sub.data.agosto <- sub.data.agosto[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.agosto, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.septiembre <- datos[datos$MES == 'septiembre',]
sub.data.septiembre <- dcast(sub.data.septiembre, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.septiembre)[3] <- "Total_Num_Ausentismo_Septiembre"
colnames(sub.data.septiembre)[1] <- "RUT"
sub.data.septiembre <- sub.data.septiembre[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.septiembre, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.octubre <- datos[datos$MES == 'octubre',]
sub.data.octubre <- dcast(sub.data.octubre, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.octubre)[3] <- "Total_Num_Ausentismo_Octubre"
colnames(sub.data.octubre)[1] <- "RUT"
sub.data.octubre <- sub.data.octubre[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.octubre, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.noviembre <- datos[datos$MES == 'noviembre',]
sub.data.noviembre <- dcast(sub.data.noviembre, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.noviembre)[3] <- "Total_Num_Ausentismo_Noviembre"
colnames(sub.data.noviembre)[1] <- "RUT"
sub.data.noviembre <- sub.data.noviembre[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.noviembre, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.diciembre <- datos[datos$MES == 'diciembre',]
sub.data.diciembre <- dcast(sub.data.diciembre, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.diciembre)[3] <- "Total_Num_Ausentismo_Diciembre"
colnames(sub.data.diciembre)[1] <- "RUT"
sub.data.diciembre <- sub.data.diciembre[,c(1,3)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.diciembre, by.x="RUT", by.y="RUT",all.x=TRUE)

# Construccion de N° ausentismos por MOTIVO DE AUSENCIA
sub.data.ACC.TRABAJO <- datos[datos$MOTIVO_AUSENCIA == 'ACC.TRABAJO',]
sub.data.ACC.TRABAJO <- dcast(sub.data.ACC.TRABAJO, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.ACC.TRABAJO)[2] <- "Ausentismo_por_ACC.TRABAJO"
colnames(sub.data.ACC.TRABAJO)[1] <- "RUT"
sub.data.ACC.TRABAJO <- sub.data.ACC.TRABAJO[,c(1,2)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.ACC.TRABAJO, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.LICENCIA <- datos[datos$MOTIVO_AUSENCIA == 'LICENCIA',]
sub.data.LICENCIA <- dcast(sub.data.LICENCIA, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.LICENCIA)[2] <- "Ausentismo_por_LICENCIA"
colnames(sub.data.LICENCIA)[1] <- "RUT"
sub.data.LICENCIA <- sub.data.LICENCIA[,c(1,2)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.LICENCIA, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.MATERNAL <- datos[datos$MOTIVO_AUSENCIA == 'MATERNAL',]
sub.data.MATERNAL <- dcast(sub.data.MATERNAL, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.MATERNAL)[2] <- "Ausentismo_por_MATERNAL"
colnames(sub.data.MATERNAL)[1] <- "RUT"
sub.data.MATERNAL <- sub.data.MATERNAL[,c(1,2)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.MATERNAL, by.x="RUT", by.y="RUT",all.x=TRUE)

sub.data.VACACIONES <- datos[datos$MOTIVO_AUSENCIA == 'VACACIONES',]
sub.data.VACACIONES <- dcast(sub.data.VACACIONES, RUT ~ Ausentismo, fun.aggregate = sum)
colnames(sub.data.VACACIONES)[2] <- "Ausentismo_por_VACACIONES"
colnames(sub.data.VACACIONES)[1] <- "RUT"
sub.data.VACACIONES <- sub.data.VACACIONES[,c(1,2)]
datos.ausentismos <- merge(datos.ausentismos, sub.data.VACACIONES, by.x="RUT", by.y="RUT",all.x=TRUE)

# Reemplaza NA por 0
datos.ausentismos[is.na(datos.ausentismos)] <- 0
  
# agregamos todas las variables de la ficha del trabajador
if('data.table' %in% rownames(installed.packages()) == FALSE) {install.packages('data.table')}
library(data.table)
ficha.trabajador <- datos[,1:27]
ficha.trabajador <- ficha.trabajador[!duplicated(ficha.trabajador$RUT),]
ficha.trabajador <- ficha.trabajador[,c(1,2,3,5,7,9,11,13,15,17,19,20,22,24,25,26,27)]

# meses trabajando desde el 01-01-2017 hasta hoy 31-08-2018
ficha.trabajador$Fecha_ing <- strptime(ficha.trabajador$Fecha_ing, format = "%d-%m-%Y")
ficha.trabajador$Meses_fin_data <-  strptime(max(datos$DATE_RPT),format = "%Y-%m-%d")

#Funcion que calcula diferencia en meses entre dos fechas
elapsed_months <- function(end_date, start_date) {
  ed <- as.POSIXlt(end_date)
  sd <- as.POSIXlt(start_date)
  12 * (ed$year - sd$year) + (ed$mon - sd$mon)
}

# mayor igual a 19 meses diferencia entre 01-01-2017 y 31-08-2018
ficha.trabajador$Meses_Laborando_2017 <- elapsed_months(ficha.trabajador$Meses_fin_data, ficha.trabajador$Fecha_ing)
ficha.trabajador$Meses_Laborando_2017 <- ifelse(ficha.trabajador$Meses_Laborando_2017 > 19, 19, ficha.trabajador$Meses_Laborando_2017)

#strptime("2018-08-31",format = "%Y-%m-%d")-strptime("2017-01-01",format = "%Y-%m-%d")
#Time difference of 607 days

ficha.trabajador$Dias_Laborando_2017 <- round(ficha.trabajador$Meses_fin_data - ficha.trabajador$Fecha_ing,0)
ficha.trabajador$Dias_Laborando_2017 <- ifelse(ficha.trabajador$Dias_Laborando_2017 > 607,607,ficha.trabajador$Dias_Laborando_2017)

datos.ausentismos <- merge(datos.ausentismos, ficha.trabajador, by.x="RUT", by.y="RUT",all.x=TRUE)
dim(datos.ausentismos)
View(datos.ausentismos)

# Ratio entre N° Ausentismos diarios dentre 2017-01-01 y 31-08-2018
datos.ausentismos$Ratio_Num_Ausent_dias_trabaj <- datos.ausentismos$Total_Num_Ausentismos/datos.ausentismos$Dias_Laborando_2017

# DIscretizando las variables continuas como EDAD y MESES TRABAJANDO del RUT
if('smbinning' %in% rownames(installed.packages()) == FALSE) {install.packages('smbinning')}
library(smbinning)
library(ggplot2)

# Histograma distribucion
plot.hist <- ggplot(data=datos.ausentismos, aes(datos.ausentismos$Total_Num_Ausentismos))  + 
  geom_histogram(breaks=seq(0, 600, by =20), 
                 col="black", 
                 aes(fill=..count..)) +
  scale_fill_gradient("N° Trab.", low = "blue", high = "red") +
  labs(title="Distribucion del N° Ausentismos del Total de Trabajadores") +
  labs(x="N° Ausentismos Historicos", y="N° Trabajadores")

print(plot.hist)
summary(datos.ausentismos$Total_Num_Ausentismos)
quantile(datos.ausentismos$Total_Num_Ausentismos,c(0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1))

#Intervalos meses antiguedad
datos.ausentismos$Intervalo_Meses_Antiguedad <- ifelse(datos.ausentismos$meses_trabajando >= 0 & datos.ausentismos$meses_trabajando <= 12,'[0,12]',
                                                       ifelse(datos.ausentismos$meses_trabajando > 12 & datos.ausentismos$meses_trabajando <= 24, ']12,24]',
                                                              ifelse(datos.ausentismos$meses_trabajando > 24 & datos.ausentismos$meses_trabajando <= 36, ']24,36]',
                                                                     ifelse(datos.ausentismos$meses_trabajando > 36 & datos.ausentismos$meses_trabajando <= 48, ']36,48]',
                                                                            ifelse(datos.ausentismos$meses_trabajando > 48 & datos.ausentismos$meses_trabajando <= 60, ']48,60]',
                                                                                   ifelse(datos.ausentismos$meses_trabajando > 60 & datos.ausentismos$meses_trabajando <= 72, ']60,72]',
                                                                                          ifelse(datos.ausentismos$meses_trabajando > 72 & datos.ausentismos$meses_trabajando <= 84, ']72,84]',
                                                                                                 ifelse(datos.ausentismos$meses_trabajando > 84 & datos.ausentismos$meses_trabajando <= 96, ']84,96]',
                                                                                                        ifelse(datos.ausentismos$meses_trabajando > 96 & datos.ausentismos$meses_trabajando <= 108, ']96,108]',
                                                                                                               ifelse(datos.ausentismos$meses_trabajando > 108 & datos.ausentismos$meses_trabajando <= 120, ']108,120]',
                                                                                                                      ifelse(datos.ausentismos$meses_trabajando > 120 & datos.ausentismos$meses_trabajando <= 240, ']120,240]',
                                                                                                                             ifelse(datos.ausentismos$meses_trabajando > 240 & datos.ausentismos$meses_trabajando <= 360, ']240,360]',
                                                                                                                                    ifelse(datos.ausentismos$meses_trabajando > 360 & datos.ausentismos$meses_trabajando <= 480, ']360,480]',
                                                                                                                                           ifelse(datos.ausentismos$meses_trabajando > 480 & datos.ausentismos$meses_trabajando <= 600, ']480,600]',
                                                                                                                                                  ']600,720]'))))))))))))))
                                                                                                        
# Histograma distribucion N° Ausentismos totales
Count_meses_antiguedad <- as.data.frame(table(datos.ausentismos$Intervalo_Meses_Antiguedad))

p = ggplot(data=Count_meses_antiguedad, 
           aes(x = reorder(Count_meses_antiguedad$Var1, Count_meses_antiguedad$Freq),
               y = Count_meses_antiguedad$Freq,
               fill = Count_meses_antiguedad$Freq)) + 
  geom_bar(stat = "identity", col="black") + 
          labs(title="Distribucion Antiguedad del Total de Trabajadores") +
          labs(x="N° meses antiguedad", y="N° Trabajadores")
p + coord_flip()

Count_meses_antiguedad

# Boxplot de N° Ausentismo por grupo de meses de antiguedad
datos.ausentismos$Intervalo_Meses_Antiguedad <- as.factor(datos.ausentismos$Intervalo_Meses_Antiguedad)

p10 <- ggplot(datos.ausentismos , aes(x = datos.ausentismos$Intervalo_Meses_Antiguedad,
                                                            y = datos.ausentismos$Total_Num_Ausentismos)) +
  geom_boxplot()
print(p10 + coord_flip())

# Boxplot Ausentismos por Sexo
datos.ausentismos$Sexo <- as.factor(datos.ausentismos$Sexo)

p11 <- ggplot(datos.ausentismos , aes(x = datos.ausentismos$Sexo,
                                      y = datos.ausentismos$Total_Num_Ausentismos)) +
  geom_boxplot()
print(p11 + coord_flip())

# Boxplot Ausentismos por Nacionalidad
datos.ausentismos$Nacion_Desc <- as.factor(datos.ausentismos$Nacion_Desc)

p12 <- ggplot(datos.ausentismos , aes(x = datos.ausentismos$Nacion_Desc,
                                      y = datos.ausentismos$Total_Num_Ausentismos)) +
  geom_boxplot()
print(p12 + coord_flip())

# Boxplot Ausentismos por Estado civil
datos.ausentismos$Est_civil_final <- as.factor(datos.ausentismos$Est_civil_final)

p13 <- ggplot(datos.ausentismos , aes(x = datos.ausentismos$Est_civil_final,
                                      y = datos.ausentismos$Total_Num_Ausentismos)) +
  geom_boxplot()
print(p13 + coord_flip())

# Boxplot Ausentismos por Estudios
datos.ausentismos$Estudios_Desc <- as.factor(datos.ausentismos$Estudios_Desc)

p14 <- ggplot(datos.ausentismos , aes(x = datos.ausentismos$Estudios_Desc,
                                      y = datos.ausentismos$Total_Num_Ausentismos)) +
  geom_boxplot()
print(p14 + coord_flip())

# Boxplot Ausentismos por Residencia
datos.ausentismos$Residencia_Trabajador <- as.factor(datos.ausentismos$Residencia_Trabajador)

p15 <- ggplot(datos.ausentismos , aes(x = datos.ausentismos$Residencia_Trabajador,
                                      y = datos.ausentismos$Total_Num_Ausentismos)) +
  geom_boxplot()
print(p15 + coord_flip())

# Boxplot Ausentismos por Jornada
datos.ausentismos$Jornada_Desc <- as.factor(datos.ausentismos$Jornada_Desc)

p16 <- ggplot(datos.ausentismos , aes(x = datos.ausentismos$Jornada_Desc,
                                      y = datos.ausentismos$Total_Num_Ausentismos)) +
  geom_boxplot()
print(p16 + coord_flip())

# Boxplot Ausentismos por Horario
datos.ausentismos$Horario_Desc <- as.factor(datos.ausentismos$Horario_Desc)

p17 <- ggplot(datos.ausentismos , aes(x = datos.ausentismos$Horario_Desc,
                                      y = datos.ausentismos$Total_Num_Ausentismos)) +
  geom_boxplot()
print(p17 + coord_flip())

# Boxplot Ausentismos por Titulo
datos.ausentismos$Titulo_Desc <- as.factor(datos.ausentismos$Titulo_Desc)

p18 <- ggplot(datos.ausentismos , aes(x = datos.ausentismos$Titulo_Desc,
                                      y = datos.ausentismos$Total_Num_Ausentismos)) +
  geom_boxplot()
print(p18 + coord_flip())

# Boxplot Ausentismos por Ocupacion
datos.ausentismos$Ocupacion <- as.factor(datos.ausentismos$Ocupacion)

p19 <- ggplot(datos.ausentismos , aes(x = datos.ausentismos$Ocupacion,
                                      y = datos.ausentismos$Total_Num_Ausentismos)) +
  geom_boxplot()
print(p19 + coord_flip())

# N° Ausentismos por MOTIVO DE AUSENCIA
#library(Rcmdr)
.Table <- with(datos[datos$Ausentismo == 1,], table(MOTIVO_AUSENCIA))
tablafreq <- as.data.frame(.Table)
porcentaje <- as.data.frame(round(100*.Table/sum(.Table), 2))
tabla_resumen <- cbind(tablafreq,Porc = porcentaje$Freq)
View(tabla_resumen)

# Boxplot Ausentismos por MES
.Table <- with(datos[datos$Ausentismo == 1,], table(MES))
tablafreq <- as.data.frame(.Table)
porcentaje <- as.data.frame(round(100*.Table/sum(.Table), 2))
tabla_resumen <- cbind(tablafreq,Porc = porcentaje$Freq)
View(tabla_resumen)

# Boxplot Ausentismos por DIA
.Table <- with(datos[datos$Ausentismo == 1,], table(DIA))
tablafreq <- as.data.frame(.Table)
porcentaje <- as.data.frame(round(100*.Table/sum(.Table), 2))
tabla_resumen <- cbind(tablafreq,Porc = porcentaje$Freq)
View(tabla_resumen)

# Contruyendo la variable TARGET FINAL                      
datos.ausentismos$Ausentismo_TARGET <- ifelse(datos.ausentismos$Total_Num_Ausentismos_1S >= 1,1,0)
datos.ausentismos$Ausentismo_TARGET <- as.factor(datos.ausentismos$Ausentismo_TARGET)
table(datos.ausentismos$Ausentismo_TARGET)

# Excluir variables que no utilizaremos para modelar
datos.ausentismos$Meses_fin_data <- NULL
datos.ausentismos$Fecha_ing <- NULL

### arbol de decision grafico
library(rpart.plot)
library(party)
library(rpart)
library(rattle)
library(randomForest)

fit2 <- rpart(Total_Num_Ausentismos_1S ~ 
                Sexo + Ausentismo_TARGET + Edad_actual + Ausentismo_por_VACACIONES
              , data=na.omit(datos.ausentismos)
              , control=rpart.control(minsplit=50, cp=0.001))

fancyRpartPlot(fit2)

# Arbol de decision para N° Ausentismo TARGET
datos.ausentismos$Ausentismo_TARGET <- as.factor(datos.ausentismos$Ausentismo_TARGET)

# Clasificacion Score Ausentismo a 1 mes

fit <- randomForest(Ausentismo_TARGET ~ 
                  Total_Num_Atrasos +
                  #Total_Num_Ausentismos_1M+Total_Num_Ausentismos_3M+Total_Num_Ausentismos_6M+Total_Num_Ausentismos_9M+Total_Num_Ausentismos_12M+
                  Total_Num_Ausentismos_2S+Total_Num_Ausentismos_3S+Total_Num_Ausentismos_4S+
                  Ausentismo_por_ACC.TRABAJO+Ausentismo_por_LICENCIA+Ausentismo_por_MATERNAL+Ausentismo_por_VACACIONES+ 
                  Total_Num_Ausentismo_Lunes+Total_Num_Ausentismo_Martes+Total_Num_Ausentismo_Miercoles+Total_Num_Ausentismo_Jueves+
                  Total_Num_Ausentismo_Viernes+Total_Num_Ausentismo_Sabado+ Total_Num_Ausentismo_Domingo+
                  Total_Num_Ausentismo_Enero+Total_Num_Ausentismo_Febrero+Total_Num_Ausentismo_Marzo+Total_Num_Ausentismo_Abril+
                  Total_Num_Ausentismo_Mayo+Total_Num_Ausentismo_Junio+Total_Num_Ausentismo_Julio+Total_Num_Ausentismo_Agosto+Total_Num_Ausentismo_Septiembre+
                  Total_Num_Ausentismo_Octubre+Total_Num_Ausentismo_Noviembre+Total_Num_Ausentismo_Diciembre+
                  Sexo + Edad_actual + Estado_Desc + Nacion_Desc + Est_civil_final + Residencia_Trabajador + Estudios_Desc + Horario_Desc + meses_trabajando, 
                  data=na.omit(datos.ausentismos),importance=TRUE)
print(fit)
importance(fit)
varImpPlot(fit)
datos.ausentismos$Score_Ausentismo_1S <- fit$votes[,2]

# Regresion N° Ausentismo a 1 semana

fit2 <- randomForest(Total_Num_Ausentismos_1S ~ 
                       Total_Num_Atrasos +
                       # Total_Num_Ausentismos_1M+Total_Num_Ausentismos_3M+Total_Num_Ausentismos_6M+Total_Num_Ausentismos_9M+Total_Num_Ausentismos_12M+
                       Total_Num_Ausentismos_2S+Total_Num_Ausentismos_3S+Total_Num_Ausentismos_4S+
                       Ausentismo_por_ACC.TRABAJO+Ausentismo_por_LICENCIA+Ausentismo_por_MATERNAL+Ausentismo_por_VACACIONES+ 
                       Total_Num_Ausentismo_Lunes+Total_Num_Ausentismo_Martes+Total_Num_Ausentismo_Miercoles+Total_Num_Ausentismo_Jueves+
                       Total_Num_Ausentismo_Viernes+Total_Num_Ausentismo_Sabado+ Total_Num_Ausentismo_Domingo+
                       Total_Num_Ausentismo_Enero+Total_Num_Ausentismo_Febrero+Total_Num_Ausentismo_Marzo+Total_Num_Ausentismo_Abril+
                       Total_Num_Ausentismo_Mayo+Total_Num_Ausentismo_Junio+Total_Num_Ausentismo_Julio+Total_Num_Ausentismo_Agosto+Total_Num_Ausentismo_Septiembre+
                       Total_Num_Ausentismo_Octubre+Total_Num_Ausentismo_Noviembre+Total_Num_Ausentismo_Diciembre+
                       Sexo + Edad_actual + Estado_Desc + Nacion_Desc + Est_civil_final + Residencia_Trabajador + Estudios_Desc + Horario_Desc + meses_trabajando, 
                     data=na.omit(datos.ausentismos),importance=TRUE)
print(fit2)
importance(fit2)
datos.ausentismos$Score_Num_Ausentismo_1S <- round(fit2$predicted,0)
View(datos.ausentismos)
# guardando los resultados
write.csv2(datos.ausentismos,'Predictor_Numero_y_Score_de_ausentismos_1_SEMANA.csv')

save.image("~/Predictor_ausentismos_1_semana.RData")
