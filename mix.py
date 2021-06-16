from gurobipy import Model, quicksum, GRB
import datetime, pandas as pd


class OptimalMix:
    def __init__(self, parameters):
        # Model
        self.model = Model()
        self.solution = []
        self.solution_dict = {}
        self.period_df = None
        self.week_df = None
        self.month_df = None
        self.cost = []

        # Static parameters
        self.Turnos = parameters['Turnos']
        self.salario = parameters['salario']
        self.largomen = parameters['largomen']
        self.largosem = parameters['largosem']
        self.cotasup = parameters['cotasup']
        self.cotainf = parameters['cotainf']
        self.diaslabmin = parameters['diaslabmin']
        self.diaslabmax = parameters['diaslabmax']
        self.zcero = parameters['zcero']
        self.productividad = parameters['productividad']
        self.ausentismo = parameters['ausentismo']
        self.rotacion = parameters['rotacion']
        self.contrato = parameters['contrato']
        self.despido = parameters['despido']
        self.Turnoshx = parameters['Turnoshx']
        self.Turnoslegales = parameters['Turnoslegales']
        self.ppto = parameters['ppto']
        self.sobrecargo = parameters['sobrecargo']
        self.cu = parameters['cu']
        self.co = parameters['co']
        self.slmin = parameters['slmin']
        self.opmin = parameters['opmin']
        self.opmax = parameters['opmax']
        self.SemCambioDotacion = int(parameters['SemCambioDotacion'])
        self.horasmensual = parameters['horasmensual']
        self.mip_gap = parameters['mip_gap']/100
        self.start_date = datetime.datetime.strptime(parameters['start_date'], '%d/%m/%Y').date()
        self.end_date = datetime.datetime.strptime(parameters['end_date'], '%d/%m/%Y').date()
        self.sheet_start_date = datetime.datetime.strptime(parameters['sheet_start_date'], '%d/%m/%Y').date()
        self.sheet_end_date = datetime.datetime.strptime(parameters['sheet_end_date'], '%d/%m/%Y').date()

        self.Turnos_not_hx = self.Turnos.copy()
        for shift in self.Turnoshx:
            self.Turnos_not_hx.remove(shift)

        # Time shifts parameters
        self.time_shifts = parameters['time_shifts']
        self.weekday_kind = parameters['weekday_kind']
        self.open_start_time = []
        self.open_end_time = []
        self.close_start_time = []
        self.close_end_time = []
        minutes_per_shift = (24 * 60)//self.time_shifts
        if not self.weekday_kind:
            timerange_parameters = ['open_start_time', 'open_end_time', 'close_start_time',
                                    'close_end_time']
            for parameter in timerange_parameters:
                aux_list = parameters[parameter].copy()
                for i in range(len(aux_list)):
                    aux_list[i] = time_to_minutes(aux_list[i]) // 60
                setattr(self, parameter, aux_list)
        else:
            timerange_parameters = ['open_start_time', 'open_end_time', 'close_start_time', 'close_end_time']
            for parameter in timerange_parameters:
                aux_list = parameters[parameter].copy()
                for i in range(7):
                    aux_list[i] = time_to_minutes(aux_list[i])//60
                setattr(self, parameter, aux_list)
        # Demand parameters
        self.aux = None
        self.demanda = None
        self.Periodos = None
        self.Semanas = None
        self.LargoDia = None
        self.Diadelasemana = None
        self.HoraPeriodo = None
        self.Dia = None
        self.Semana = None
        self.Periodossalida = None
        self.Periodocerrado = None
        self.Aperturacierre = None
        self.Inicios = None
        self.Fines = None
        self.Tini = None
        self.Tfin = None
        self.Semini = None
        self.G4Semini = None
        self.G4sem = None
        self.G4Dom = None
        self.Periodosabiertos = None
        self.NotG4Semini = None
        self.x = None
        self.z = None
        self.hx = None
        self.hc = None
        self.hxacum = None
        self.hxv = None
        self.ymas = None
        self.ymenos = None
        self.ingreso = None
        self.nuevoscontratos = None
        self.nuevosdespidos = None
        self.egreso = None
        self.oferta = None
        self.CambiosDota = None
        self.NotCambiosDota = None

    def load_demand(self, dataframe):
        left_slice = (self.start_date - self.sheet_start_date).days
        right_slice = left_slice + (self.end_date - self.start_date).days + 1
        df2 = dataframe.iloc[left_slice:right_slice, 2:]
        demands = df2.values.tolist()
        self.Demandas = demands
        self.demanda = [val for sublist in self.Demandas for val in sublist]
        #print(left_slice)
        #print(right_slice)
        #print(self.Demandas)
        print('len(self.demanda)', len(self.demanda))
        self.Semanas = int(len(self.Demandas) / 7)
        self.LargoDia = len(self.Demandas[0])
        self.HoraPeriodo = 24 // self.LargoDia

        # 1 = Lunes, 2 = Martes ... etc
        self.Diadelasemana = self.start_date.weekday() + 1
        # Dias[j]f

        self.Dia = [[i+1 + (j-1)*self.LargoDia for i in range(self.LargoDia)] for j in range(self.Semanas*7+2)]
        self.Dia[0] = []

        # Semana[j]
        self.Semana = [[i+1 + (j-1)*self.LargoDia*7 for i in range(self.LargoDia*7)] for j in range(self.Semanas+1)]
        self.Semana[0]=[]

        # Periodos
        # self.Periodos = [i for i in range(1, self.Semanas*self.LargoDia*7+self.LargoDia+1)]
        self.Periodos = [i for i in range(1, len(self.Demandas) * self.LargoDia + 1)]

        # Periodossalida
        self.Periodossalida = self.Periodos[4:]

        # Periodocerrado
        self.Periodocerrado = []

        # Aperturacierre
        self.Aperturacierre = [i for i in range(2,len(self.Periodos)+1, self.LargoDia)]+[j for j in range(self.LargoDia-1, len(self.Periodos)+1, self.LargoDia)]
        self.Aperturacierre.sort()

        # Inicios
        #self.Inicios = [4 * i for i in range(1, int(len(self.Periodos) / 4))]
        self.Inicios = []
        for k in range(len(self.open_start_time)):
            self.Inicios += [int(i * (self.LargoDia / 24)) + self.LargoDia * j for j in
                             range(0, int(len(self.Periodos) / self.LargoDia)) for i in
                             range(int(self.open_start_time[k]), int(self.open_end_time[k]) + 1,
                                   int(24 / self.LargoDia))]
        self.Inicios.sort()

        # Fines
        #self.Fines = [4 * i for i in range(2, int(len(self.Periodos) / 4))]
        self.Fines = []
        for k in range(len(self.close_start_time)):
            self.Fines += [int(i * (self.LargoDia / 24)) + self.LargoDia * j for j in
                           range(0, int(len(self.Periodos) / self.LargoDia)) for i in
                           range(int(self.close_start_time[k]), int(self.close_end_time[k]) + 1,
                                int(24 / self.LargoDia))]
        self.Fines.sort()

        # Tini
        self.Tini = [i for i in range(1,len(self.Periodos),self.LargoDia)]

        # Tfin
        self.Tfin = [i for i in range(self.LargoDia,len(self.Periodos)+1,self.LargoDia)]

        # Semini
        self.Semini = [i for i in range(1,len(self.Periodos)-self.LargoDia, self.LargoDia*7)]


        # G4Semini
        self.G4Semini = [i for i in range(1,len(self.Periodos)+1, self.LargoDia*7*4)]

        # G4sem[j]
        self.G4sem = [[i+1 + j*self.LargoDia*7*4 for i in range(self.LargoDia*7*4)] for j in range(self.Semanas//4)]
        self.G4sem.append([])

        # G4Dom
        self.G4Dom = [[i + 1 + (j - 1) * self.LargoDia * 7 for k in range(4) for i in
                       range(self.LargoDia * (7 * (k + 1) - self.Diadelasemana),
                             self.LargoDia * (1 + 7 * (k + 1) - self.Diadelasemana))] for j in range(self.Semanas - 2)]
        self.G4Dom[0] = []

        self.Periodosabiertos = list(set(self.Periodos) - set(self.Periodocerrado))
        self.NotG4Semini = list(set(self.Periodos) - set(self.G4Semini))

        # CambiosDota
        self.CambiosDota = [i for i in range(1, len(self.Periodos) + 1, self.LargoDia * 7 * self.SemCambioDotacion)]
        self.NotCambiosDota = list(set(self.Periodos) - set(self.CambiosDota))
        self._add_vars_to_model()

    def _add_vars_to_model(self):
        self.z = self.model.addVars(self.Periodos, self.Turnos, name="z", vtype="I")
        self.aux = self.model.addVars([4, 8], vtype=GRB.BINARY)
        self.x = self.model.addVars(self.Periodos, self.Turnos, name="x", vtype="I")
        self.hx = self.model.addVars(self.Periodos, self.Turnos,  name="hx", vtype="C")
        self.hc = self.model.addVars(self.Periodos, self.Turnos, name="hc", vtype="C")
        self.hxacum = self.model.addVars(self.Periodos, self.Turnos, name="hxacum",
                                         vtype="C")
        self.hxv = self.model.addVars(self.Periodos, self.Turnos, name="hxv", vtype="C")
        self.ymas = self.model.addVars(self.Periodos, name="ymas", vtype="C")
        self.ymenos = self.model.addVars(self.Periodos, name="ymenos", vtype="C")
        self.ingreso = self.model.addVars(self.Periodos, self.Turnos, name="ingreso", vtype="I")
        self.nuevoscontratos = self.model.addVars(self.Periodos, self.Turnos, name="nuevoscontratos", vtype="I")
        self.nuevosdespidos = self.model.addVars(self.Periodos, self.Turnos, name="nuevosdespidos", vtype="I")
        self.egreso = self.model.addVars(self.Periodos, self.Turnos, name="egreso", vtype="I")
        self.oferta = self.model.addVars(self.Periodos, self.Turnos, name="oferta", vtype="C")
        # Los valores de todo lo referido a horas (cotasup,cotainf,largosem,largomen,sobrecargo están multiplicados por un factor en las restricciones/F.O., por lo que aquí no es necesario hacer modificaciones respecto a lo que está escrito en los formularios)

    def load_constrains(self):
        self.model.setObjective(
            quicksum(self.z[t, i] * self.salario[i] for t in self.G4Semini for i in
                     self.Turnos) + quicksum(
                self.nuevoscontratos[t, i] * self.contrato[i] + self.nuevosdespidos[t, i] *
                self.despido[i] + self.HoraPeriodo * (
                        self.cu * self.ymenos[t] + self.co * self.ymas[t] + (
                        self.hx[t, i] - self.hc[t, i]) * self.sobrecargo * self.salario[
                            i] / self.largomen[i]) for t in
                self.Periodos for i in
                self.Turnoshx), GRB.MINIMIZE)


#        self.model.addConstrs((self.nuevoscontratos[t, i] == 0 for t in self.CambiosDota for i in self.Turnos))
#        self.model.addConstrs((self.nuevosdespidos[t, i] == 0 for t in self.CambiosDota for i in self.Turnos))        
        


        self.model.addConstrs(
            (self.hx[t, i] <= self.egreso[t - 1, i] + self.hx[t - 1, i] + self.ingreso[t + 1, i] +
             self.hx[t + 1, i] for
             t in range(2, len(self.Periodos)) for i in self.Turnoshx), name="hx1")
        self.model.addConstrs(
            (self.hc[t, i] <= self.ingreso[t, i] + self.egreso[t, i] + self.hc[t - 1, i] + self.hc[
                t + 1, i] for t in
             range(2, len(self.Periodos)) for i in self.Turnoshx), name="hx2")
        #self.model.addConstrs(
           # (quicksum(self.hx[r, i] for r in range(t, t + self.LargoDia * 7) if r < len(self.Periodos)) <= self.z[t, i] for t
           #  in
           #  self.Semini for i in self.Turnoshx), name="hx3")
        self.model.addConstrs(
            (self.hxv[t, i] >= self.hxacum[t - self.LargoDia * 7 * 4, i] - quicksum(
                self.hc[r, i] + self.hxv[r, i] for r in range(t - (self.LargoDia * 7 * 4 + 1), t))
             for i in self.Turnoshx for t
             in range(self.LargoDia * 7 * 4 + 2, len(self.Periodos))), name="hx4")
        self.model.addConstrs((self.hxacum[1, i] == 0 for i in self.Turnoshx), name="hx5")
        self.model.addConstrs((self.hxacum[t, i] == self.hxacum[t - 1, i] + self.hx[t, i] -
                               self.hc[t, i] - self.hxv[
                                   t, i] for i in self.Turnoshx for t in
                               range(2, len(self.Periodos))), name="hx6")
        self.model.addConstrs(
            (self.hc[t, i] <= self.hxacum[t - 1, i] + self.hx[t, i] - self.hxv[
                t - 1, i] for i in self.Turnoshx for t in range(2, len(self.Periodos))), name="hx7")
                
        self.model.addConstrs(
            (quicksum(self.hx[r,i] for r in range(t,t+self.LargoDia*7) if r < len(self.Periodos) for i in
                self.Turnoshx) <= quicksum(self.x[r,i] for r in range(t,t+self.LargoDia*7) if r < len(self.Periodos) for i in self.Turnoshx)/10 for t in self.Semini))

         
        #self.model.addConstr(self.aux.sum() == 1)
        #self.model.addConstrs((quicksum(self.x[r,i] for r in range(t,t+self.LargoDia)) == self.z[t,i]/self.HoraPeriodo*quicksum(self.aux[j] * j for j
        #    in [4, 8]) for t in self.Tini for i in self.Turnos))
             
             
             
             
        # Límite de stock, SIEMPRE
        self.model.addConstrs(
            (self.x[t, i] + self.hx[t, i] <= self.z[t, i] for t in self.Periodos for i in self.Turnos), "Stock")

        # Definición de oferta, SIEMPRE
        self.model.addConstrs(
            (self.oferta[t, i] <= self.productividad[i] * self.rotacion[i] * self.ausentismo[i] * (
                        self.x[t, i] + self.hx[t, i] - self.hc[t, i]) for t in
             self.Periodos for i in self.Turnos), name="roferta")
        self.model.addConstrs(
            (self.oferta[t, i] >= self.productividad[i] * self.rotacion[i] * self.ausentismo[i] * (
                        self.x[t, i] + self.hx[t, i] - self.hc[t, i]) for t in
             self.Periodos for i in self.Turnos), name="roferta2")

        # Definición de ymas e ymenos SIEMPRE
        self.model.addConstrs((self.demanda[t - 1] - quicksum(self.oferta[t, i] for i in self.Turnos) <= self.ymenos[t] for t in self.Periodos))
        self.model.addConstrs((quicksum(self.oferta[t, i] - self.demanda[t - 1] for i in self.Turnos) <= self.ymas[t] for t in self.Periodos))
        self.model.addConstrs((self.ymenos[t] <= self.demanda[t - 1] for t in self.Periodos))

        # Restricciones de flujo SIEMPRE
        self.model.addConstrs((self.ingreso[t + 1, i] >= self.x[t + 1, i] - self.x[t, i] for t in range(1, len(self.Periodos) - 1) for i in self.Turnos), name="defngreso")
        self.model.addConstrs((self.egreso[t, i] >= self.x[t, i] - self.x[t + 1, i] for t in range(1, len(self.Periodos) - 1) for i in self.Turnos),
                     name="defegres")

        # Más restricciones de flujo SIEMPRE
        self.model.addConstrs(
            (self.x[t, i] - self.x[t + 1, i] <= self.x[t - 1, i] for t in range(4, len(self.Periodos)) for i in
             self.Turnos), name="Flujo1")
        self.model.addConstrs(
            (self.x[t, i] - self.x[t + 1, i] <= self.x[t - 2, i] for t in range(4, len(self.Periodos)) for i in
             self.Turnos), name="Flujo2")
        self.model.addConstrs(
            (self.x[t, i] - self.x[t + 2, i] <= self.x[t - 1, i] for t in range(4, len(self.Periodos) - 1) for i in
             self.Turnos), name="Flujoss1")
        self.model.addConstrs(
            (self.x[t, i] - self.x[t + 3, i] <= self.x[t - 1, i] for t in range(4, len(self.Periodos) - 2) for i in
             self.Turnos), name="Flujoss32")

        # Horarios de entrada y salida SIEMPRE
        self.model.addConstrs((self.x[t, i] - self.x[t + 1, i] <= 0 for t in self.Inicios if (t > 0 and t+1 <= len(self.Periodos)) for i in self.Turnos), name="soloentrar")
        self.model.addConstrs((self.x[t, i] - self.x[t + 1, i] >= 0 for t in self.Fines if (t > 0 and t+1 <= len(self.Periodos)) for i in self.Turnos), name="solosalir")

        # restricciones legales SIEMPRE
        # los fulltime no pueden trabajar mas de 2 domingos seguidos SIEMPRE
        for i in range(1, self.Semanas - 2):
            self.model.addConstrs((2 * self.z[self.LargoDia * 4 + self.LargoDia * 7 * (i - 1), j] *
                                  self.cotasup[j] / self.HoraPeriodo >= quicksum(
                        self.x[t, j] for t in self.G4Dom[i]) for j in self.Turnoslegales))
        # Tope de horas de trabajo al día y a la semana SIEMPRE
        self.model.addConstrs(
            (quicksum(self.x[r, i] for r in range(t, t + self.LargoDia)) <= self.cotasup[i] * self.z[t, i] / self.HoraPeriodo for t
             in self.Tini for i in
             self.Turnos))
        self.model.addConstrs(
            (quicksum(self.x[r,i] for r in range(t,t+self.LargoDia)) >= self.cotainf[i]*self.z[t,i]/self.HoraPeriodo for t
             in self.Tini for i in
             self.Turnos))
     


        # Límite de ingresos semanales SIEMPRE
        for i in self.Turnos:
            self.model.addConstrs((sum(self.ingreso[r, i] for r in range(t, t + self.LargoDia * 7) if r < len(self.Periodos)) <= self.diaslabmax[
                i] * sum(self.x[r, i] * self.HoraPeriodo / self.largosem[i] for r in range(t, t + self.LargoDia * 7) if r < len(self.Periodos)) for t in
                                   self.Semini))
            self.model.addConstrs((sum(self.ingreso[r, i] for r in range(t, t + self.LargoDia * 7) if r < len(self.Periodos)) >= self.diaslabmin[
                i] * sum(self.x[r, i] * self.HoraPeriodo / self.largosem[i] for r in range(t, t + self.LargoDia * 7) if r < len(self.Periodos)) for t in
                                   self.Semini))



        # Restricción service level SIEMPRE
        self.model.addConstrs((sum(self.ymenos[r] for r in range(t, t + self.LargoDia)) / (
                    0.000001 + sum(self.demanda[r - 1] for r in range(t, t + self.LargoDia))) <= 1 - self.slmin for t in
                               self.Tini), name="niveldeservicio")

        # Definición de nuevos contratos, y restricción de solo contratar o despedir en principios de mes SIEMPRE
        self.model.addConstrs(
            (self.z[t, i] == self.z[t - 1, i] + self.nuevoscontratos[t, i] - self.nuevosdespidos[t, i] for i in
             self.Turnos for t in range(2, len(self.Periodos) + 1)))
        self.model.addConstrs(
            (self.z[1, i] == self.zcero[i] + self.nuevoscontratos[1, i] - self.nuevosdespidos[1, i] for i in
             self.Turnos))
        self.model.addConstrs((self.nuevoscontratos[t, i] == 0 for t in self.NotCambiosDota for i in self.Turnos))
        self.model.addConstrs((self.nuevosdespidos[t, i] == 0 for t in self.NotCambiosDota for i in self.Turnos))

        # Limite mínimo de operación
        self.model.addConstrs((quicksum(self.x[t, i] for i in self.Turnos) >= self.opmin for t in self.Periodosabiertos))

        # Limite máximo de operación
        #self.model.addConstrs((quicksum(self.x[t, i] for i in self.Turnos) <= self.opmax for t in self.Periodosabiertos))




        # RESTRICCIONES OPCIONALES
        #if self.constraint_extra_hours:
        #    self.model.addConstrs((self.hx[t, "fulltime"] == 0 for t in self.Periodos))
        #    self.model.addConstrs((self.hc[t, i] == 0 for t in self.Periodos for i in self.Turnos))
        #    self.model.addConstrs((self.hxv[t, i] == 0 for t in self.Periodos for i in self.Turnos))
        self.model.addConstrs((self.hx[t, i] == 0 for t in self.Periodos for i in self.Turnos_not_hx))
        self.model.addConstrs((self.hc[t, i] == 0 for t in self.Periodos for i in self.Turnos_not_hx))
        self.model.addConstrs((self.hxv[t, i] == 0 for t in self.Periodos for i in self.Turnos_not_hx))
        self.model.addConstrs((self.hxacum[t, i] == 0 for t in self.Periodos for i in self.Turnos_not_hx))

        # restriccion proporcional OPCIONAL
        #if self.constraint_proportional:
        #    self.model.addConstrs((self.z[t, "fulltime"] >= 0.7 * quicksum(self.z[t, i] for i in self.Turnos) for t in self.Periodos))
        #    self.model.addConstrs((self.z[t, "fulltime"] <= 0.8 * quicksum(self.z[t, i] for i in self.Turnos) for t in self.Periodos))

        #if self.constraint_only_fulltime_extra_hours:
        #    self.model.addConstrs((self.hx[t, i] == 0 for t in self.Periodos for i in self.Turnos if i != "fulltime"))

        self.model.setParam('MIPGap', self.mip_gap)
        self.model.setParam('Threads', 3)

    def run_mix(self):
        self.model.optimize()
        for v in self.model.getVars():
            if hasattr(v, 'X'):
                self.solution_dict[v.varName] = v.X
                self.solution.append((v.varName, v.X))

    def get_solution(self):
        return self.solution


def time_to_minutes(str_time):
    values = str_time.split(":")
    return int(values[0]) * 60 + int(values[1])
