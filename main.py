//+------------------------------------------------------------------+
//|                                Grid_Slave_Copier_Multi.mq5       |
//|        Local Basket TP Calculation for Perfect Execution         |
//+------------------------------------------------------------------+
#property copyright "Your Custom EA"
#property version   "3.1"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

input string InpApiUrl      = "https://your-api-name.onrender.com"; 
input int    InpMagicNumber = 123456; 

CTrade         trade;
CPositionInfo  pos;

ulong  last_processed_signal_id = 0;
string g_auth_status            = "CHECKING...";
int    g_days_remaining         = 0;
long   g_account_number         = 0;
double g_LiveTP_USD             = 4.20; // Default $4.20 target

string SendAPIRequest(string endpoint) {
   char post[], result[]; string headers;
   string sep = (StringFind(endpoint, "?") >= 0) ? "&" : "?";
   string full_url = InpApiUrl + endpoint + sep + "t=" + IntegerToString(GetTickCount());
   int res = WebRequest("GET", full_url, NULL, NULL, 5000, post, 0, result, headers);
   if(res == 200) return CharArrayToString(result);
   return "";
}

int OnInit() {
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_account_number = AccountInfoInteger(ACCOUNT_LOGIN);
   
   ChartSetInteger(0, CHART_SHOW_TRADE_LEVELS, false);
   ChartSetInteger(0, CHART_SHOW_OBJECT_DESCR, true);
   ChartSetInteger(0, CHART_MODE, CHART_CANDLES);
   ChartSetInteger(0, CHART_COLOR_CANDLE_BULL, clrMediumSeaGreen);
   ChartSetInteger(0, CHART_COLOR_CANDLE_BEAR, clrFireBrick);
   ChartSetInteger(0, CHART_COLOR_CHART_UP, clrMediumSeaGreen);
   ChartSetInteger(0, CHART_COLOR_CHART_DOWN, clrFireBrick);

   EventSetMillisecondTimer(1000);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
   EventKillTimer();
   DeleteCustomTradeLines();
   Comment("");
}

double DollarsToPoints(double usd_amount) {
   return (_Point > 0) ? (usd_amount / _Point) : 420.0;
}

void CloseAllBySide(long side) {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      if(pos.SelectByIndex(i) && pos.Symbol() == _Symbol && pos.Magic() == InpMagicNumber && pos.PositionType() == side) {
         trade.PositionClose(pos.Ticket());
      }
   }
}

// Automatically calculates exact TP based on Slave's OWN average price
void UpdateLocalBasketTP(long position_type) {
   double total_vol = 0;
   double total_val = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      if(pos.SelectByIndex(i) && pos.Symbol() == _Symbol && pos.Magic() == InpMagicNumber && pos.PositionType() == position_type) {
         total_vol += pos.Volume();
         total_val += (pos.PriceOpen() * pos.Volume());
      }
   }

   if(total_vol == 0) return;

   double avg_price = total_val / total_vol;
   double tp_pts = DollarsToPoints(g_LiveTP_USD);
   double new_tp = NormalizeDouble(avg_price + ((position_type == POSITION_TYPE_BUY ? 1 : -1) * tp_pts * _Point), _Digits);

   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      if(pos.SelectByIndex(i) && pos.Symbol() == _Symbol && pos.Magic() == InpMagicNumber && pos.PositionType() == position_type) {
         if(MathAbs(pos.TakeProfit() - new_tp) > _Point / 2) {
            trade.PositionModify(pos.Ticket(), 0, new_tp);
         }
      }
   }
}

void OnTimer() {
   string endpoint = StringFormat("/api/state?account=%d", g_account_number);
   string data = SendAPIRequest(endpoint);
   if(data == "") return; 
   
   string pairs[];
   int count = StringSplit(data, '|', pairs);
   
   string current_signal = "NONE";
   ulong current_signal_id = 0;
   
   for(int i=0; i<count; i++) {
      string kv[];
      if(StringSplit(pairs[i], '=', kv) == 2) {
         if(kv[0] == "AUTH") g_auth_status = kv[1];
         else if(kv[0] == "DAYS") g_days_remaining = (int)StringToInteger(kv[1]);
         else if(kv[0] == "SIGNAL") current_signal = kv[1];
         else if(kv[0] == "SIGNAL_ID") current_signal_id = (ulong)StringToInteger(kv[1]);
         else if(kv[0] == "TP_VAL") g_LiveTP_USD = StringToDouble(kv[1]);
      }
   }

   if(g_auth_status != "OK") return; 

   if(current_signal != "NONE" && current_signal_id > last_processed_signal_id) {
      string cmd_parts[];
      StringSplit(current_signal, '_', cmd_parts);
      
      if(cmd_parts[0] == "BUY") trade.Buy(StringToDouble(cmd_parts[1]), _Symbol, 0, 0, 0); 
      else if(cmd_parts[0] == "SELL") trade.Sell(StringToDouble(cmd_parts[1]), _Symbol, 0, 0, 0);
      else if(cmd_parts[0] == "CLOSE" && cmd_parts[1] == "BUY") CloseAllBySide(POSITION_TYPE_BUY);
      else if(cmd_parts[0] == "CLOSE" && cmd_parts[1] == "SELL") CloseAllBySide(POSITION_TYPE_SELL);
      
      last_processed_signal_id = current_signal_id;
   }
}

void DrawCustomTradeLines() {
   double buy_tp = 0, sell_tp = 0;
   int active_buys = 0, active_sells = 0;

   for(int i=0; i<PositionsTotal(); i++) {
      if(pos.SelectByIndex(i) && pos.Symbol() == _Symbol && pos.Magic() == InpMagicNumber) {
         ulong ticket = pos.Ticket(); double price = pos.PriceOpen();
         long type = pos.PositionType(); double vol = pos.Volume(); double tp = pos.TakeProfit();

         string line_name = "Vis_Entry_" + IntegerToString((long)ticket);

         if(ObjectFind(0, line_name) < 0) {
            ObjectCreate(0, line_name, OBJ_HLINE, 0, 0, price);
            ObjectSetInteger(0, line_name, OBJPROP_STYLE, STYLE_DOT); 
            ObjectSetInteger(0, line_name, OBJPROP_WIDTH, 1);
            ObjectSetInteger(0, line_name, OBJPROP_HIDDEN, true);      
            ObjectSetInteger(0, line_name, OBJPROP_SELECTABLE, false);
         }
         ObjectSetDouble(0, line_name, OBJPROP_PRICE, price);

         if(type == POSITION_TYPE_BUY) {
            ObjectSetInteger(0, line_name, OBJPROP_COLOR, clrDodgerBlue); 
            ObjectSetString(0, line_name, OBJPROP_TEXT, StringFormat("Buy %.2f", vol));
            if(tp > 0) buy_tp = tp; active_buys++;
         } else if(type == POSITION_TYPE_SELL) {
            ObjectSetInteger(0, line_name, OBJPROP_COLOR, clrRed); 
            ObjectSetString(0, line_name, OBJPROP_TEXT, StringFormat("Sell %.2f", vol));
            if(tp > 0) sell_tp = tp; active_sells++;
         }
      }
   }

   if(active_buys > 0 && buy_tp > 0) {
      if(ObjectFind(0, "Vis_TP_Buy") < 0) {
         ObjectCreate(0, "Vis_TP_Buy", OBJ_HLINE, 0, 0, buy_tp);
         ObjectSetInteger(0, "Vis_TP_Buy", OBJPROP_COLOR, clrGold); 
         ObjectSetInteger(0, "Vis_TP_Buy", OBJPROP_STYLE, STYLE_SOLID); ObjectSetInteger(0, "Vis_TP_Buy", OBJPROP_WIDTH, 2);
         ObjectSetInteger(0, "Vis_TP_Buy", OBJPROP_HIDDEN, true); ObjectSetInteger(0, "Vis_TP_Buy", OBJPROP_SELECTABLE, false);
      }
      ObjectSetDouble(0, "Vis_TP_Buy", OBJPROP_PRICE, buy_tp); ObjectSetString(0, "Vis_TP_Buy", OBJPROP_TEXT, "BUY BASKET TP");
   } else ObjectDelete(0, "Vis_TP_Buy");

   if(active_sells > 0 && sell_tp > 0) {
      if(ObjectFind(0, "Vis_TP_Sell") < 0) {
         ObjectCreate(0, "Vis_TP_Sell", OBJ_HLINE, 0, 0, sell_tp);
         ObjectSetInteger(0, "Vis_TP_Sell", OBJPROP_COLOR, clrGold); 
         ObjectSetInteger(0, "Vis_TP_Sell", OBJPROP_STYLE, STYLE_SOLID); ObjectSetInteger(0, "Vis_TP_Sell", OBJPROP_WIDTH, 2);
         ObjectSetInteger(0, "Vis_TP_Sell", OBJPROP_HIDDEN, true); ObjectSetInteger(0, "Vis_TP_Sell", OBJPROP_SELECTABLE, false);
      }
      ObjectSetDouble(0, "Vis_TP_Sell", OBJPROP_PRICE, sell_tp); ObjectSetString(0, "Vis_TP_Sell", OBJPROP_TEXT, "SELL BASKET TP");
   } else ObjectDelete(0, "Vis_TP_Sell");

   for(int i = ObjectsTotal(0, 0, OBJ_HLINE) - 1; i >= 0; i--) {
      string obj_name = ObjectName(0, i, 0, OBJ_HLINE);
      if(StringFind(obj_name, "Vis_Entry_") == 0) {
         ulong ticket = (ulong)StringToInteger(StringSubstr(obj_name, 10));
         if(!PositionSelectByTicket(ticket)) ObjectDelete(0, obj_name);
      }
   }
}

void DeleteCustomTradeLines() {
   ObjectDelete(0, "Vis_TP_Buy"); ObjectDelete(0, "Vis_TP_Sell");
   for(int i = ObjectsTotal(0, 0, OBJ_HLINE) - 1; i >= 0; i--) {
      string obj_name = ObjectName(0, i, 0, OBJ_HLINE);
      if(StringFind(obj_name, "Vis_Entry_") == 0) ObjectDelete(0, obj_name);
   }
}

void OnTick() {
   // Recalculate TP locally on every tick
   UpdateLocalBasketTP(POSITION_TYPE_BUY);
   UpdateLocalBasketTP(POSITION_TYPE_SELL);
   
   DrawCustomTradeLines(); 
   
   string status_msg;
   if(g_auth_status == "OK") {
      status_msg = StringFormat("ACTIVE - SUBSCRIPTION OK (%d Days Left)", g_days_remaining);
   } else if(g_auth_status == "EXPIRED") {
      status_msg = "EXPIRED - PLEASE RENEW YOUR SUBSCRIPTION";
   } else {
      status_msg = "ACCESS DENIED - ACCOUNT NOT REGISTERED";
   }

   Comment(StringFormat(
      "============================================\n" +
      " SLAVE COPIER SUBSCRIPTION SYSTEM           \n" +
      "============================================\n" +
      " MT5 Account No  : %d\n" +
      " Target Basket TP: $%.2f\n" +
      " License Status  : %s\n" +
      "============================================",
      g_account_number, g_LiveTP_USD, status_msg
   ));
}
