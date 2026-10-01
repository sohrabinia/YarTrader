#property strict
#property version "1.1"
#property description "YarTrader MT4 SIGNAL/data bridge - read only, fail closed"

#define AUTH_ACCOUNT 143056202
string AUTH_SERVER = "Alpari-Pro.ECN";
string REQ_FILE = "yartrader_mt4_request.txt";
string HEARTBEAT_FILE = "yartrader_mt4_heartbeat.txt";

int OnInit(){
   if(IsDemo() || AccountNumber()!=AUTH_ACCOUNT || AccountServer()!=AUTH_SERVER){
      Print("YarTrader MT4 SIGNAL bridge REFUSED: account/server/live-role check failed.");
      return(INIT_FAILED);
   }
   EventSetTimer(1);
   WriteHeartbeat();
   return(INIT_SUCCEEDED);
}
void OnDeinit(const int reason){ EventKillTimer(); FileDelete(HEARTBEAT_FILE,FILE_COMMON); }
void OnTick(){ WriteHeartbeat(); ProcessRequest(); }
void OnTimer(){ WriteHeartbeat(); ProcessRequest(); }
bool Authorized(){ return(!IsDemo() && AccountNumber()==AUTH_ACCOUNT && AccountServer()==AUTH_SERVER); }

void WriteHeartbeat(){
   if(!Authorized()) return;
   int h=FileOpen(HEARTBEAT_FILE,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE) return;
   string sym=Symbol();
   double bid=MarketInfo(sym,MODE_BID);
   double ask=MarketInfo(sym,MODE_ASK);
   FileWriteString(h,IntegerToString(AccountNumber())+"|"+AccountServer()+"|0|"+sym+"|"+
      DoubleToString(bid,Digits)+"|"+DoubleToString(ask,Digits)+"|"+IntegerToString((int)TimeCurrent()));
   FileFlush(h);
   FileClose(h);
}

void Respond(string id,string payload){
   int h=FileOpen("yartrader_mt4_response_"+id+".txt",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE) return;
   FileWriteString(h,id+"|"+payload); FileFlush(h); FileClose(h);
}

int TfMinutes(string tf){
   if(tf=="M1") return 1; if(tf=="M5") return 5; if(tf=="M15") return 15;
   if(tf=="M30") return 30; if(tf=="H1") return 60; if(tf=="H4") return 240;
   if(tf=="D1") return 1440; if(tf=="W1") return 10080; if(tf=="MN1") return 43200;
   return 0;
}
int TfCode(string tf){
   if(tf=="M1") return PERIOD_M1; if(tf=="M5") return PERIOD_M5; if(tf=="M15") return PERIOD_M15;
   if(tf=="M30") return PERIOD_M30; if(tf=="H1") return PERIOD_H1; if(tf=="H4") return PERIOD_H4;
   if(tf=="D1") return PERIOD_D1; if(tf=="W1") return PERIOD_W1; if(tf=="MN1") return PERIOD_MN1;
   return 0;
}
void ProcessRequest(){
   if(!Authorized() || !FileIsExist(REQ_FILE,FILE_COMMON)) return;
   int h=FileOpen(REQ_FILE,FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE) return;
   string line=FileReadString(h); FileClose(h); FileDelete(REQ_FILE,FILE_COMMON);
   string p[]; int n=StringSplit(line,StringGetCharacter("|",0),p); if(n<2) return;
   string id=p[0], op=p[1];
   if(op=="HISTORY" && n>=5){
      string sym=p[2], tf=p[3]; int bars=(int)StrToInteger(p[4]); int minutes=TfMinutes(tf);
      if(minutes<=0 || bars<=0 || StringLen(sym)==0){ Respond(id,"ERROR|BAD_REQUEST"); return; }
      ResetLastError();
      if(!SymbolSelect(sym,true)){ Respond(id,"ERROR|SYMBOL_SELECT"); return; }
      int tfCode=TfCode(tf);
      int available=iBars(sym,tfCode);
      if(available<=0){ Respond(id,"ERROR|NO_HISTORY"); return; }
      int targetIndex=MathMin(available-1,MathMax(0,bars-1));
      datetime oldest=iTime(sym,tfCode,targetIndex);
      if(oldest<=0){ Respond(id,"ERROR|NO_HISTORY"); return; }
      Respond(id,"OK|"+sym+"|"+tf+"|"+IntegerToString(available)+"|"+
         IntegerToString((int)oldest)+"|"+IntegerToString(minutes));
      return;
   }
   if(op=="ACCOUNT"){
      Respond(id,"OK|"+IntegerToString(AccountNumber())+"|"+AccountServer()+"|0|"+DoubleToString(AccountBalance(),2));
      return;
   }
   Respond(id,"ERROR|READ_ONLY_SIGNAL_BRIDGE");
}
