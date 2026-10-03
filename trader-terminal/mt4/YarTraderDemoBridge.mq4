#property strict
#property version "1.1"
#property description "YarTrader MT4 DEMO bridge - fail closed"

#define AUTH_ACCOUNT 252031952
string AUTH_SERVER = "Alpari-Pro.ECN-Demo";
string REQ_FILE = "yartrader_mt4_request.txt";
string HEARTBEAT_FILE = "yartrader_mt4_heartbeat.txt";

int OnInit()
{
   if(!IsDemo() || AccountNumber()!=AUTH_ACCOUNT || AccountServer()!=AUTH_SERVER)
   {
      Print("YarTrader MT4 DEMO bridge REFUSED: account/server/demo check failed.");
      return(INIT_FAILED);
   }
   EventSetTimer(1); WriteHeartbeat();
   Print("YarTrader MT4 DEMO bridge ready for account ",AccountNumber()," on ",AccountServer());
   return(INIT_SUCCEEDED);
}
void OnDeinit(const int reason){ EventKillTimer(); }
void OnTick(){ WriteHeartbeat(); ProcessRequest(); }
void OnTimer(){ WriteHeartbeat(); ProcessRequest(); }
bool Authorized(){ return(IsDemo() && AccountNumber()==AUTH_ACCOUNT && AccountServer()==AUTH_SERVER); }

void WriteHeartbeat()
{
   if(!Authorized()) return;
   string sym="XAUUSD";
   double bid=MarketInfo(sym,MODE_BID), ask=MarketInfo(sym,MODE_ASK);
   int h=FileOpen(HEARTBEAT_FILE,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE) return;
   FileWriteString(h,IntegerToString(AccountNumber())+"|"+AccountServer()+"|1|"+sym+"|"+
                   DoubleToString(bid,Digits)+"|"+DoubleToString(ask,Digits)+"|"+
                   IntegerToString((int)TimeCurrent()));
   FileFlush(h); FileClose(h);
}
void Respond(string id,string payload)
{
   int h=FileOpen("yartrader_mt4_response_"+id+".txt",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE) return;
   FileWriteString(h,id+"|"+payload); FileFlush(h); FileClose(h);
}
void ProcessRequest()
{
   if(!Authorized() || !FileIsExist(REQ_FILE,FILE_COMMON)) return;
   int h=FileOpen(REQ_FILE,FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE) return;
   string line=FileReadString(h); FileClose(h);
   if(StringLen(line)<3) return;
   FileDelete(REQ_FILE,FILE_COMMON);
   string p[]; int n=StringSplit(line,StringGetCharacter("|",0),p);
   if(n<2) return;
   string id=p[0], op=p[1];

   if(op=="ACCOUNT"){ Respond(id,"OK|"+IntegerToString(AccountNumber())+"|"+AccountServer()+"|1|"+DoubleToString(AccountBalance(),2)); return; }

   if(op=="HISTORY" && n>=5)
   {
      string sym=p[2], tf=p[3]; int bars=(int)StrToInteger(p[4]);
      int code=TfCode(tf); int mins=TfMinutes(tf);
      if(code==0 || mins<=0 || bars<=0 || StringLen(sym)==0){ Respond(id,"ERROR|BAD_REQUEST"); return; }
      if(!SymbolSelect(sym,true)){ Respond(id,"ERROR|SYMBOL_SELECT"); return; }
      long serverFirst=0; SeriesInfoInteger(sym,PERIOD_M1,SERIES_SERVER_FIRSTDATE,serverFirst);
      datetime requestedFirst=(datetime)(TimeCurrent()-(long)bars*mins*60);
      datetime probe[1]; int copied=0,lastErr=0,available=0; datetime oldest=0;
      for(int i=0;i<180;i++)
      {
         ResetLastError(); copied=CopyTime(sym,code,requestedFirst,1,probe); lastErr=GetLastError();
         available=iBars(sym,code);
         if(copied>0 && available>0)
         {
            oldest=iTime(sym,code,available-1);
            if(oldest>0 && oldest<=requestedFirst) break;
         }
         if(available>0){ datetime t=iTime(sym,code,available-1); if(t>0) oldest=t; }
         Sleep(1000);
      }
      available=iBars(sym,code);
      if(available<=0 || oldest<=0){ Respond(id,"ERROR|NO_HISTORY|"+IntegerToString(lastErr)); return; }
      if(oldest>requestedFirst)
      {
         Respond(id,"ERROR|HISTORY_INCOMPLETE|"+IntegerToString(available)+"|"+
                     IntegerToString((int)oldest)+"|"+IntegerToString(mins)+"|"+
                     IntegerToString((int)serverFirst)+"|"+IntegerToString(lastErr));
         return;
      }
      Respond(id,"OK|"+sym+"|"+tf+"|"+IntegerToString(available)+"|"+
                  IntegerToString((int)oldest)+"|"+IntegerToString(mins)+"|"+
                  IntegerToString((int)serverFirst));
      return;
   }

   if(op=="TICK" && n>=3)
   {
      string sym=p[2]; double bid=MarketInfo(sym,MODE_BID), ask=MarketInfo(sym,MODE_ASK);
      if(bid<=0 || ask<=0){ Respond(id,"ERROR|NO_TICK"); return; }
      Respond(id,"OK|"+sym+"|"+DoubleToString(bid,Digits)+"|"+DoubleToString(ask,Digits)+"|"+IntegerToString((int)TimeCurrent())); return;
   }
   if(op=="POSITIONS")
   {
      string sym=(n>=3?p[2]:""), data="";
      for(int i=OrdersTotal()-1;i>=0;i--)
      {
         if(!OrderSelect(i,SELECT_BY_POS,MODE_TRADES)) continue;
         if(OrderSymbol()!=sym && sym!="") continue;
         int t=OrderType(); if(t!=OP_BUY && t!=OP_SELL) continue;
         if(StringLen(data)>0) data+=";";
         data+=IntegerToString(OrderTicket())+","+IntegerToString(t)+","+DoubleToString(OrderLots(),2)+","+
               DoubleToString(OrderOpenPrice(),Digits)+","+IntegerToString((int)OrderOpenTime());
      }
      Respond(id,"OK|"+data); return;
   }
   if(op=="ORDER" && n>=9)
   {
      string sym=p[2]; if(sym!="XAUUSD"){ Respond(id,"ERROR|SYMBOL_NOT_AUTHORIZED"); return; }
      int type=(p[3]=="BUY"?OP_BUY:OP_SELL); double lots=StrToDouble(p[4]);
      double price=type==OP_BUY?MarketInfo(sym,MODE_ASK):MarketInfo(sym,MODE_BID);
      double sl=StrToDouble(p[6]), tp=StrToDouble(p[7]); int magic=(int)StrToInteger(p[8]);
      ResetLastError(); int ticket=OrderSend(sym,type,lots,price,5,sl,tp,"YarTrader DEMO",magic,0,clrNONE); int err=GetLastError();
      if(ticket<0){ Respond(id,"ERROR|"+IntegerToString(err)); return; }
      Respond(id,"OK|"+IntegerToString(ticket)+"|"+DoubleToString(price,Digits)+"|"+DoubleToString(lots,2)); return;
   }
   if(op=="CLOSE" && n>=4)
   {
      int ticket=(int)StrToInteger(p[2]); double requested=StrToDouble(p[3]);
      if(!OrderSelect(ticket,SELECT_BY_TICKET)){ Respond(id,"ERROR|POSITION_NOT_FOUND"); return; }
      if(OrderSymbol()!="XAUUSD" || (OrderType()!=OP_BUY && OrderType()!=OP_SELL)){ Respond(id,"ERROR|POSITION_NOT_AUTHORIZED"); return; }
      double lots=OrderLots(); if(requested>0 && MathAbs(requested-lots)>0.0000001){ Respond(id,"ERROR|VOLUME_MISMATCH"); return; }
      double price=OrderType()==OP_BUY?MarketInfo(OrderSymbol(),MODE_BID):MarketInfo(OrderSymbol(),MODE_ASK);
      ResetLastError(); bool ok=OrderClose(ticket,lots,price,5,clrNONE); int err=GetLastError();
      if(!ok){ Respond(id,"ERROR|"+IntegerToString(err)); return; }
      Respond(id,"OK|"+IntegerToString(ticket)+"|"+DoubleToString(price,Digits)+"|"+DoubleToString(lots,2)); return;
   }
   Respond(id,"ERROR|UNKNOWN_OPERATION");
}
int TfMinutes(string tf){if(tf=="M1")return 1;if(tf=="M5")return 5;if(tf=="M15")return 15;if(tf=="M30")return 30;if(tf=="H1")return 60;if(tf=="H4")return 240;if(tf=="D1")return 1440;if(tf=="W1")return 10080;if(tf=="MN1")return 43200;return 0;}
int TfCode(string tf){if(tf=="M1")return PERIOD_M1;if(tf=="M5")return PERIOD_M5;if(tf=="M15")return PERIOD_M15;if(tf=="M30")return PERIOD_M30;if(tf=="H1")return PERIOD_H1;if(tf=="H4")return PERIOD_H4;if(tf=="D1")return PERIOD_D1;if(tf=="W1")return PERIOD_W1;if(tf=="MN1")return PERIOD_MN1;return 0;}
